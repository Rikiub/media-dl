import concurrent.futures as cf
import logging
import shutil
import time
from pathlib import Path
from typing import Literal, cast

from media_dl._ydl import (
    parse_output_template,
    run_postproces,
    download_thumbnail,
    download_subtitle,
)
from media_dl.downloader.internal import DownloadCallback, ProgressStatus, YDLDownloader
from media_dl.downloader.config import FormatConfig
from media_dl.downloader.progress import DownloadProgress
from media_dl.exceptions import MediaError
from media_dl.models.format import AudioFormat, Format, FormatList, VideoFormat
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStream, Stream
from media_dl.types import StrPath, FILE_FORMAT
from media_dl.path import get_tempfile

log = logging.getLogger(__name__)

PROGRESS_STATUS = Literal[
    "downloading",
    "processing",
    "finished",
]

ExtractResult = Playlist | list[LazyStream] | Stream


def _gen_postprocessing_dict(stream: Stream, format: Format) -> dict:
    d = stream.model_dump(by_alias=True)

    if format:
        d |= format.model_dump(by_alias=True)

    return d


class StreamDownloader:
    """Multi-thread stream downloader.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: File format to search or convert with (FFmpeg) if is a extension.
        quality: Quality to filter.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
        threads: Maximum processes to execute.
        show_progress: Choice if render download progress.

    Raises:
        FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
    """

    def __init__(
        self,
        format: FILE_FORMAT = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        ffmpeg: StrPath | None = None,
        metadata: bool = True,
        threads: int = 4,
        show_progress: bool = True,
    ):
        self.config = FormatConfig(
            format=format,
            quality=quality,
            output=Path(output),
            ffmpeg=Path(ffmpeg) if ffmpeg else None,
            metadata=metadata,
        )
        self._threads = threads
        self._progress = DownloadProgress(disable=not show_progress)

        log.debug("Download config: %s", self.config.as_dict())

    def download_all(self, media: ExtractResult) -> list[Path]:
        """Download any result.

        Returns:
            List of paths to downloaded files.

        Raises:
            MediaError: Something bad happens when download.
        """

        streams = self._media_to_list(media)
        paths: list[Path] = []

        log.debug("Founded %s entries.", len(streams))
        self._progress.counter.reset(len(streams))

        with self._progress:
            with cf.ThreadPoolExecutor(max_workers=self._threads) as executor:
                futures = [
                    executor.submit(self._download_work, task) for task in streams
                ]

                success = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        try:
                            paths.append(ft.result())
                            success += 1
                        except MediaError:
                            errors += 1
                except (cf.CancelledError, KeyboardInterrupt):
                    log.warning(
                        "❗ Canceling downloads... (press Ctrl+C again to force)"
                    )
                    raise KeyboardInterrupt()
                finally:
                    executor.shutdown(wait=True, cancel_futures=True)

                    log.debug(
                        "%s of %s streams completed. %s errors.",
                        success,
                        len(streams),
                        errors,
                    )
        return paths

    def download(
        self,
        stream: Stream,
        on_progress: DownloadCallback | None = None,
    ) -> Path:
        """Download a single `Stream` result.

        Args:
            stream: Target `Stream` to download.
            format: Specific `Stream` format to download. By default will select BEST format.
            on_progress: Callback function to get download progress information.

        Returns:
            Path to downloaded file.

        Raises:
            MediaError: Something bad happens when download.
            ValueError: Provided `Format` wasn't founded in `Stream`.
        """

        with self._progress:
            self._progress.counter.reset(total=1)
            return self._download_work(stream, on_progress=on_progress)

    def _download_work(
        self,
        stream: LazyStream | Stream,
        on_progress: DownloadCallback | None = None,
    ) -> Path:
        task_id = self._progress.add_task(
            description=stream.display_name or "Fetching...",
            status="Started",
            step="",
        )

        real_stream = stream

        try:
            # Resolve stream
            if type(stream) is LazyStream:
                real_stream = stream.fetch()
                self._progress.update(task_id, description=real_stream.display_name)
            elif isinstance(stream, Stream):
                real_stream = stream
            else:
                raise TypeError(stream)

            log.debug('"%s": Downloading stream.', real_stream.id)

            # Resolve formats
            format_video, format_audio, download_config = self._resolve_format(
                real_stream
            )

            # STATUS: Download
            self._progress.update(task_id, status="Downloading")

            [
                self._log_format(real_stream.id, f)
                for f in (format_video, format_audio)
                if f is not None
            ]

            # Add callbacks
            callbacks = []

            def p(p: ProgressStatus):
                step = ""
                if p.steps_total > 1:
                    step = f"({p.steps_completed}/{p.steps_total})"

                return self._progress.update(
                    task_id,
                    completed=p.downloaded_bytes,
                    total=p.total_bytes,
                    step=step,
                )

            callbacks.append(p)

            if on_progress:
                callbacks.append(on_progress)

            # Downloader config
            merge_format = None
            if format_video and format_audio and download_config.convert:
                merge_format = download_config.convert

            if (
                download_config.type == "audio"
                and format_audio
                and not download_config.convert
            ):
                format_video = None

            # Run download
            d = YDLDownloader(
                filepath=get_tempfile(),
                video=format_video,
                audio=format_audio,
                merge_format=merge_format,
                callbacks=callbacks,
            )
            downloaded_file = d.run()
            progress_data = d.progress

            # STATUS: Postprocess
            if on_progress:
                progress_data.status = "postprocessing"
                on_progress(progress_data)
            self._progress.update(task_id, status="Processing")
            log.debug('"%s": Postprocessing downloaded file.', real_stream.id)

            stream_dict = real_stream.model_dump(by_alias=True)

            if format_video:
                stream_dict |= _gen_postprocessing_dict(real_stream, format_video)
            elif format_audio:
                stream_dict |= _gen_postprocessing_dict(real_stream, format_audio)

            # Final filename
            output_name = parse_output_template(stream_dict, "%(uploader)s - %(title)s")

            # Download resources
            if d := download_thumbnail(output_name, stream_dict):
                log.debug('"%s": Thumbnail downloaded: "%s"', real_stream.id, d)
            if d := real_stream.subtitles and download_subtitle(
                output_name, stream_dict
            ):
                log.debug('"%s": Subtitle downloaded: "%s"', real_stream.id, d)

            # Run postprocessing
            params = download_config.ydl_params(music_meta=real_stream._is_music_site())

            downloaded_file = run_postproces(
                file=downloaded_file,
                info=stream_dict,
                params=params,
            )
            log.debug(
                '"%s": Postprocessing finished, saved as "%s".',
                real_stream.id,
                downloaded_file.suffix[1:],
            )

            # STATUS: Finish
            final_path = Path(self.config.output, output_name + downloaded_file.suffix)

            # Check if file is duplicate
            if final_path.exists():
                self._progress.update(task_id, status="Skipped")
                log.info(
                    'Skipped: "%s" (Exists as "%s").',
                    real_stream.display_name,
                    final_path.suffix[1:],
                )
            # Move file
            else:
                self.config.output.mkdir(parents=True, exist_ok=True)

                downloaded_file = downloaded_file.rename(
                    downloaded_file.parent / final_path.name
                )
                final_path = shutil.move(downloaded_file, final_path)

                self._progress.update(task_id, status="Finished")
                log.info('Finished: "%s".', real_stream.display_name)

            if on_progress:
                progress_data.status = "finished"
                on_progress(progress_data)

            return final_path
        except MediaError as err:
            log.error('Error: "%s": %s', real_stream.display_name, str(err))
            self._progress.update(task_id, status="Error")
            raise
        finally:
            self._progress.counter.advance()
            time.sleep(1.0)
            self._progress.remove_task(task_id)

    def _media_to_list(self, media: ExtractResult) -> list[Stream]:
        streams = []

        match media:
            case Stream():
                streams = [media]
            case Playlist():
                streams = media.streams
            case list():
                streams = media

        if not streams:
            raise TypeError(media)

        return streams  # type: ignore

    def _resolve_format(
        self,
        stream: Stream,
        video: VideoFormat | None = None,
        audio: AudioFormat | None = None,
    ) -> tuple[VideoFormat | None, AudioFormat | None, FormatConfig]:
        config = self.config
        selected_format = config.format

        if not video:
            config.format = "video"
            video = cast(
                VideoFormat | None, self._extract_best_format(stream.formats, config)
            )

        if not audio:
            config.format = "audio"
            audio = cast(
                AudioFormat | None, self._extract_best_format(stream.formats, config)
            )

        config.format = selected_format

        if not config.convert:
            if audio and stream._is_music_site():
                log.debug('"%s": Detected as music site.', stream.id)

                log.debug(
                    '"%s": Config changed to "audio".',
                    stream.id,
                )

                config.format = "audio"
            elif video:
                config.format = "video"
            elif audio:
                config.format = "audio"

        return video, audio, config

    def _extract_best_format(
        self, formats: FormatList, config: FormatConfig
    ) -> Format | None:
        """Extract best format in stream formats."""

        # Filter by extension
        if f := config.convert and formats.filter(extension=config.convert):
            format = f
        # Filter by type
        elif f := formats.filter(type=config.type):
            format = f
        else:
            return None

        if config.quality:
            return format.get_closest_quality(config.quality)
        else:
            return format[-1]

    def _log_format(self, stream_id: str, format: Format) -> None:
        log.debug(
            '"%s": Download %s format "%s" (%s %s)',
            stream_id,
            "video" if isinstance(format, VideoFormat) else "audio",
            format.id,
            format.extension,
            format.display_quality,
        )
