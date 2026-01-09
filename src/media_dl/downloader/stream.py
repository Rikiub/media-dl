from collections.abc import Callable
import concurrent.futures as cf
import shutil
import time
from pathlib import Path
from typing import cast

from loguru import logger

from media_dl.downloader.config import FormatConfig
from media_dl.downloader.internal import (
    DownloadCallback,
    ProgressStatus,
    download_formats,
)
from media_dl.downloader.metadata import download_subtitles, download_thumbnails
from media_dl.downloader.progress import DownloadProgress
from media_dl.exceptions import DownloadError, OutputTemplateError
from media_dl.models.formats.list import FormatList
from media_dl.models.formats.types import AudioFormat, Format, VideoFormat
from media_dl.models.list import BaseList, Playlist
from media_dl.models.stream import LazyStream, Stream
from media_dl.path import get_tempfile
from media_dl.template.parser import generate_output_template
from media_dl.types import FILE_FORMAT, StrPath
from media_dl.ydl.helpers import run_postproces
from media_dl.ydl.types import SupportedExtensions

ExtractResult = BaseList | LazyStream


class StreamDownloader:
    """Multi-thread stream downloader.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: File format to search or convert with (FFmpeg) if is a extension.
        quality: Quality to filter.
        output: Directory where to save files.
        threads: Maximum processes to execute.
        ffmpeg_path: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
        show_progress: Choice if render download progress.

    Raises:
        FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
    """

    def __init__(
        self,
        format: FILE_FORMAT = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        threads: int = 4,
        use_cache: bool = True,
        ffmpeg_path: StrPath | None = None,
        embed_metadata: bool = True,
        show_progress: bool = True,
    ):
        self.config = FormatConfig(
            format=format,
            quality=quality,
            output=Path(output),
            ffmpeg_path=Path(ffmpeg_path) if ffmpeg_path else None,
            embed_metadata=embed_metadata,
        )
        self.cache = use_cache
        self.threads = threads
        self._progress = DownloadProgress(disable=not show_progress)

        logger.debug("Download config: {config}", config=self.config.to_dict())

    def download_all(self, media: ExtractResult) -> list[Path]:
        """Download any result.

        Returns:
            List of paths to downloaded files.

        Raises:
            MediaError: Something bad happens when download.
        """

        playlist = media if isinstance(media, Playlist) else None
        streams = _media_to_list(media)
        paths: list[Path] = []

        logger.debug("Founded {length} entries.", length=len(streams))
        self._progress.counter.reset(len(streams), visible=bool(playlist))

        with self._progress:
            with cf.ThreadPoolExecutor(max_workers=self.threads) as executor:
                futures = [
                    executor.submit(self._download_work, task, playlist)
                    for task in streams
                ]

                success = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        try:
                            paths.append(ft.result())
                            success += 1
                        except ConnectionError:
                            errors += 1
                except OutputTemplateError as err:
                    logger.error(str(err).strip('"'))
                    raise SystemExit()
                except (cf.CancelledError, KeyboardInterrupt):
                    logger.warning(
                        "❗ Canceling downloads... (press Ctrl+C again to force)"
                    )
                    raise KeyboardInterrupt()
                finally:
                    executor.shutdown(wait=True, cancel_futures=True)

                    logger.debug(
                        "{current} of {total} streams completed. {errors} errors.",
                        current=success,
                        total=len(streams),
                        errors=errors,
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
            self._progress.counter.reset(total=1, visible=False)
            return self._download_work(stream, on_progress=on_progress)

    def _download_work(
        self,
        stream: LazyStream,
        playlist: Playlist | None = None,
        on_progress: DownloadCallback | None = None,
    ) -> Path:
        task_id = self._progress.add_task(
            description=_stream_display_name(stream) or "Fetching...",
            status="Fetching",
            step="",
        )

        full_stream = stream

        try:
            # Resolve stream
            if type(stream) is LazyStream:
                full_stream = stream.fetch(self.cache)
                self._progress.update(
                    task_id, description=_stream_display_name(full_stream)
                )
            elif isinstance(stream, Stream):
                full_stream = stream
            else:
                raise TypeError(stream)

            _log_stream(stream, "Downloading stream.")

            # Resolve formats
            format_video, format_audio, download_config = self._resolve_format(
                full_stream
            )

            # STATUS: Download
            # Add callbacks
            callbacks: list[Callable] = []

            def p(p: ProgressStatus):
                if p.steps_total > 1:
                    step = f"({p.steps_completed}/{p.steps_total})"
                else:
                    step = ""

                return self._progress.update(
                    task_id,
                    completed=p.downloaded_bytes,
                    total=p.total_bytes,
                    status=p.status.capitalize(),
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

            # Generate filename
            if download_config.output.is_dir():
                # Default template
                output = str(download_config.output) + "/" + "{uploader} - {title}"
            else:
                # User template
                output = str(download_config.output)

            output = generate_output_template(
                output=output,
                stream=full_stream,
                playlist=playlist,
                format=format_video or format_audio,
            )

            # Check if file is duplicated by name
            for file in output.parent.iterdir():
                if file.is_file() and file.stem == output.name:
                    if (
                        download_config.type == "video"
                        and file.suffix[1:] in SupportedExtensions.video
                        or download_config.type == "audio"
                        and file.suffix[1:] in SupportedExtensions.audio
                    ):
                        self._progress.update(task_id, status="Skipped")
                        logger.info(
                            'Skipped: "{stream}" (Exists as "{extension}").',
                            stream=_stream_display_name(full_stream),
                            extension=file.suffix[1:],
                        )
                        return file

            [
                _log_stream(
                    stream,
                    'Downloading {type} format "{format_id}" (extension:{format_extension} | quality:{format_quality})',
                    type="video" if isinstance(fmt, VideoFormat) else "audio",
                    format_id=fmt.id,
                    format_extension=fmt.extension,
                    format_quality=fmt.display_quality,
                )
                for fmt in (format_video, format_audio)
                if fmt is not None
            ]

            # Run download
            downloaded_file, progress = download_formats(
                filepath=get_tempfile(),
                video=format_video,
                audio=format_audio,
                merge_format=merge_format,
                callbacks=callbacks,
            )

            # STATUS: Postprocess
            if on_progress:
                progress.status = "postprocessing"
                on_progress(progress)
            self._progress.update(task_id, status="Processing")
            _log_stream(stream, "Postprocessing downloaded file.")

            # Download resources
            if file := full_stream.thumbnails and download_thumbnails(
                downloaded_file,
                full_stream.thumbnails,
            ):
                _log_stream(
                    stream,
                    'Thumbnail downloaded: "{file}"',
                    id=full_stream.id,
                    file=file,
                )

            if file := full_stream.subtitles and download_subtitles(
                downloaded_file,
                full_stream.subtitles,
            ):
                _log_stream(
                    stream,
                    'Subtitle downloaded: "{file}"',
                    id=full_stream.id,
                    file=file,
                )

            # Run postprocessing
            temp_dict = full_stream.to_ydl_dict()

            if format_video:
                temp_dict |= format_video.to_ydl_dict()
            elif format_audio:
                temp_dict |= format_audio.to_ydl_dict()

            downloaded_file = run_postproces(
                file=downloaded_file,
                info=temp_dict,
                params=download_config.ydl_params(music_metadata=full_stream.is_music),
            )

            # Add extension to filepath
            output = output.parent / f"{output.name}{downloaded_file.suffix}"
            _log_stream(
                stream,
                'Final filepath will be "{filepath}"',
                id=full_stream.id,
                filepath=output,
            )

            _log_stream(
                stream,
                'Postprocessing finished, saved as "{extension}".',
                id=full_stream.id,
                extension=downloaded_file.suffix[1:],
            )

            # STATUS: Finish
            output.parent.mkdir(parents=True, exist_ok=True)
            output = Path(shutil.move(downloaded_file, output))

            self._progress.update(task_id, status="Finished")
            logger.info(
                'Finished: "{stream}".', stream=_stream_display_name(full_stream)
            )

            if on_progress:
                progress.status = "finished"
                on_progress(progress)

            return output
        except ConnectionError as err:
            logger.error(
                'Error: "{stream}": {error}',
                stream=_stream_display_name(full_stream),
                error=str(err),
            )
            self._progress.update(task_id, status="Error")
            raise DownloadError(str(err))
        finally:
            self._progress.counter.advance()
            time.sleep(1.0)
            self._progress.remove_task(task_id)

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
            if audio and stream.is_music:
                _log_stream(stream, "Detected as music site.", id=stream.id)
                _log_stream(stream, 'Config changed to "audio".', id=stream.id)
                config.format = "audio"
            elif audio and config.format == "audio":
                config.format = "audio"
            elif video:
                config.format = "video"

        return video, audio, config

    def _extract_best_format(
        self, formats: FormatList, config: FormatConfig
    ) -> Format | None:
        """Extract best format in stream formats."""

        # Filter by extension
        if f := config.convert and formats.filter(extension=config.convert):
            format = f

        # Filter by type
        elif f := config.type == "video" and formats.only_video():
            format = f
        elif f := config.type == "audio" and formats.only_audio():
            format = f
        else:
            return None

        if config.quality:
            return format.get_closest_quality(config.quality)
        else:
            return format[0]


def _log_stream(stream: LazyStream, log: str, **kwargs):
    text = f'"{stream.id}": {log}'
    logger.debug(text, **kwargs)


def _media_to_list(media: ExtractResult) -> list[LazyStream]:
    streams = []

    match media:
        case LazyStream():
            streams = [media]
        case BaseList():
            streams = media.streams
        case _:
            raise TypeError(media)

    return streams


def _stream_display_name(stream: LazyStream) -> str:
    """Get pretty representation of the stream name."""

    if stream.is_music and stream.uploader and stream.title:
        return stream.title + " - " + stream.uploader
    elif stream.title:
        return stream.title
    else:
        return ""
