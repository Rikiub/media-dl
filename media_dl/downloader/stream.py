import concurrent.futures as cf
import logging
import shutil
import time
from pathlib import Path
from typing import Callable, Literal

from media_dl._ydl import (
    parse_output_template,
    run_postproces,
    download_thumbnail,
    download_subtitle,
)
from media_dl.downloader import internal
from media_dl.downloader.config import FormatConfig
from media_dl.exceptions import MediaError
from media_dl.models.format import AudioFormat, Format, FormatList, VideoFormat
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStreams, Stream
from media_dl.types import StrPath, FILE_FORMAT
from media_dl.path import get_tempfile
from media_dl.rich import DownloadProgress

log = logging.getLogger(__name__)

PROGRESS_STATUS = Literal[
    "downloading",
    "processing",
    "finished",
]
ProgressCallback = Callable[[PROGRESS_STATUS, int, int], None]

ExtractResult = Playlist | LazyStreams | Stream


class StreamDownloader:
    """Multi-thread stream downloader.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: File format to search or convert with (ffmpeg) if is a extension.
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
        on_progress: ProgressCallback | None = None,
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
        stream: Stream,
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        task_id = self._progress.add_task(
            description=stream.display_name or "Fetching...", status="Started"
        )

        try:
            # Resolve stream
            if type(stream) is not Stream:
                stream = stream.fetch()
                self._progress.update(task_id, description=stream.display_name)

            log.debug('"%s": Downloading stream.', stream.id)

            # Resolve formats
            format_video, format_audio, download_config = self._resolve_format(stream)

            # STATUS: Download
            self._progress.update(task_id, status="Downloading")

            if format_video:
                self._log_format(stream.id, format_video)
            if format_audio:
                self._log_format(stream.id, format_audio)

            # Configure callbacks
            total_filesize: int = 0

            def update_filesize(filesize: int):
                nonlocal total_filesize
                total_filesize = filesize

            callbacks = [
                lambda _, filesize: update_filesize(filesize),
                lambda completed, total: self._progress.update(
                    task_id, completed=completed, total=total
                ),
            ]
            if on_progress:
                callbacks.append(
                    lambda completed, total: on_progress(
                        "downloading", completed, total
                    )
                )

            if format_video and format_audio and download_config.convert:
                merge_format = download_config.convert
            else:
                merge_format = None

            if (
                download_config.type == "audio"
                and format_audio
                and not download_config.convert
            ):
                format_video = None

            # Run download
            downloaded_file = internal.download(
                filepath=get_tempfile(),
                video=format_video,
                audio=format_audio,
                merge_format=merge_format,
                callbacks=callbacks,
            )

            # STATUS: Postprocess
            if on_progress:
                on_progress("processing", total_filesize, total_filesize)
            self._progress.update(task_id, status="Processing")
            log.debug('"%s": Postprocessing downloaded file.', stream.id)

            # Final filename
            output_name = parse_output_template(
                stream._extra_info, "%(uploader)s - %(title)s"
            )

            # Download resources
            if d := download_thumbnail(output_name, stream._extra_info):
                log.debug('"%s": Thumbnail downloaded: "%s"', stream.id, d)
            if d := stream.subtitles and download_subtitle(
                output_name, stream._extra_info
            ):
                log.debug('"%s": Subtitle downloaded: "%s"', stream.id, d)

            # Run postprocessing
            params = download_config.ydl_params(music_meta=stream._is_music_site())

            downloaded_file = run_postproces(
                file=downloaded_file,
                info=stream._extra_info,
                params=params,
            )
            log.debug(
                '"%s": Postprocessing finished, saved as "%s".',
                stream.id,
                downloaded_file.suffix[1:],
            )

            # STATUS: Finish
            final_path = Path(self.config.output, output_name + downloaded_file.suffix)

            # Check if file is duplicate
            if final_path.exists():
                self._progress.update(task_id, status="Skipped")
                log.info(
                    'Skipped: "%s" (Exists as "%s").',
                    stream.display_name,
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
                log.info('Finished: "%s".', stream.display_name)

            if on_progress:
                on_progress("finished", total_filesize, total_filesize)

            return final_path
        except MediaError as err:
            log.error('Error: "%s": %s', stream.display_name, str(err))
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
            case LazyStreams():
                streams = media.root
            case Playlist():
                streams = media.streams.root

        if not streams:
            raise TypeError(media)

        return streams  # type: ignore

    def _resolve_format(
        self,
        stream: Stream,
        video: Format | None = None,
        audio: Format | None = None,
    ) -> tuple[Format | None, Format | None, FormatConfig]:
        config = self.config
        selected_format = config.format

        if not video:
            config.format = "video"
            video = self._extract_best_format(stream.formats, config)

        if not audio:
            config.format = "audio"
            audio = self._extract_best_format(stream.formats, config)

        config.format = selected_format

        if not config.convert:
            if stream._is_music_site():
                log.debug('"%s": Detected music site', stream.id)

                if not audio:
                    raise MediaError(
                        "Stream is a music site but audio format wasn't founded."
                    )

                log.debug(
                    '"%s": Change config to "audio".',
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

    def _get_format_type(self, format) -> str:
        match format:
            case VideoFormat():
                type = "video"
            case AudioFormat():
                type = "audio"
            case _:
                type = "unkdown"

        return type

    def _log_format(self, stream_id: str, format: Format) -> None:
        log.debug(
            '"%s": Download %s format "%s" (%s %s)',
            stream_id,
            self._get_format_type(format),
            format.id,
            format.extension,
            format.display_quality,
        )
