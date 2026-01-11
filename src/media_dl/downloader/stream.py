import concurrent.futures as cf
import shutil
from pathlib import Path
from typing import cast

from loguru import logger
from media_dl.downloader.config import FormatConfig
from media_dl.downloader.status import ProgressCallback
from media_dl.exceptions import DownloadError, OutputTemplateError
from media_dl.models.formats.list import FormatList
from media_dl.models.formats.types import AudioFormat, Format, VideoFormat
from media_dl.models.list import BaseList, LazyPlaylist, Playlist
from media_dl.models.progress.format import FormatStatus, VideoFormatStatus
from media_dl.models.progress.status import (
    CompletedState,
    DownloadingState,
    ErrorState,
    MergingState,
    ProcessorType,
    ResolvedState,
    ExtractingState,
    ProcessingState,
    ProgressDownloadCallback,
    SkippedState,
)
from media_dl.models.stream import LazyStream, Stream
from media_dl.path import get_tempfile
from media_dl.postprocessor import PostProcessor
from media_dl.template.parser import generate_output_template
from media_dl.types import FILE_FORMAT, StrPath
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
        self.show_progress = show_progress

        logger.debug("Download config: {config}", config=self.config.to_dict())

    def download_all(self, media: ExtractResult) -> list[Path]:
        """Download any result.

        Returns:
            List of paths to downloaded files.

        Raises:
            MediaError: Something bad happens when download.
        """

        playlist = media if isinstance(media, LazyPlaylist) else None
        streams = _media_to_list(media)
        paths: list[Path] = []

        logger.debug("Founded {length} entries.", length=len(streams))

        progress = ProgressCallback(disable=not self.show_progress)
        progress.counter.reset(len(streams), visible=bool(playlist))

        with progress:
            with cf.ThreadPoolExecutor(max_workers=self.threads) as executor:
                futures = [
                    executor.submit(self._download_work, task, progress, playlist)
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
        on_progress: ProgressDownloadCallback | None = None,
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

        if on_progress:
            return self._download_work(stream, on_progress=on_progress)
        else:
            progress = ProgressCallback(disable=not self.show_progress)
            progress.counter.reset(total=1, visible=False)
            return self._download_work(stream, on_progress=progress)

    def _download_work(
        self,
        stream: LazyStream,
        on_progress: ProgressDownloadCallback,
        playlist: LazyPlaylist | None = None,
    ) -> Path:
        on_progress(ExtractingState(id=stream.id, stream=stream))
        full_stream = stream

        try:
            # Resolve Stream
            if type(stream) is LazyStream:
                full_stream = stream.resolve(self.cache)
            elif isinstance(stream, Stream):
                full_stream = stream
            else:
                raise TypeError(stream)

            # Resolve Playlist
            if type(playlist) is LazyPlaylist:
                full_playlist = playlist.resolve(self.cache)
            elif isinstance(playlist, Playlist):
                full_playlist = playlist
            else:
                full_playlist = None

            on_progress(ResolvedState(id=stream.id, stream=full_stream))

            # Resolve formats
            video_format, audio_format, download_config = self._resolve_format(
                full_stream
            )

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
                playlist=full_playlist,
                format=video_format or audio_format,
            )

            # Check if file is duplicated by name
            for meta in output.parent.iterdir():
                if meta.is_file() and meta.stem == output.name:
                    if (
                        download_config.type == "video"
                        and meta.suffix[1:] in SupportedExtensions.video
                        or download_config.type == "audio"
                        and meta.suffix[1:] in SupportedExtensions.audio
                    ):
                        on_progress(SkippedState(id=stream.id, filepath=meta))
                        return meta

            # STATUS: Download
            def download_callback(format: FormatStatus, container: DownloadingState):
                if isinstance(format, VideoFormatStatus):
                    container.video_format = format
                else:
                    container.audio_format = format
                on_progress(container)

            downloaded = DownloadingState(id=stream.id, current_step="video")

            if download_config.type == "audio" and audio_format:
                downloaded.current_step = "audio"
                downloaded.audio_format = FormatStatus(type="audio")

                _log_download(full_stream, audio_format)

                downloaded_file = audio_format.download(
                    get_tempfile(),
                    lambda f, c=downloaded: download_callback(f, c),
                )
                downloaded.steps_completed += 1
                on_progress(downloaded)
            elif video_format:
                video_file = None
                audio_file = None

                if audio_format:
                    downloaded.steps_total = 2
                    _log_download(full_stream, audio_format)

                    downloaded.current_step = "audio"
                    downloaded.audio_format = FormatStatus(type="audio")

                    audio_file = audio_format.download(
                        get_tempfile(),
                        lambda f, c=downloaded: download_callback(f, c),
                    )
                    downloaded.steps_completed += 1

                # Video
                _log_download(full_stream, video_format)

                downloaded.current_step = "video"
                downloaded.video_format = VideoFormatStatus(type="video")
                video_file = video_format.download(
                    get_tempfile(),
                    lambda f, c=downloaded: download_callback(f, c),
                )

                downloaded.steps_completed += 1
                on_progress(downloaded)

                if (video_format and video_file) and (audio_format and audio_file):
                    # Merge
                    on_progress(
                        MergingState(
                            id=stream.id,
                            video_format=video_format,
                            audio_format=audio_format,
                        )
                    )

                    pp = PostProcessor.from_formats_merge(
                        get_tempfile(),
                        merge_format=download_config.convert or "mp4",
                        formats=[
                            (video_format, video_file),
                            (audio_format, audio_file),
                        ],
                    )
                    downloaded_file = pp.filepath
                else:
                    downloaded_file = video_file
            else:
                raise DownloadError("Formats not founded.")

            # STATUS: Postprocess
            # Run postprocessing
            if download_config.ffmpeg_path:
                pp = PostProcessor(
                    downloaded_file,
                    download_config.ffmpeg_path,
                )

                def on_state(type: ProcessorType):
                    return on_progress(
                        ProcessingState(
                            id=stream.id,
                            filepath=pp.filepath,
                            processor=type,
                        )
                    )

                if download_config.type == "video" and video_format:
                    pp.remux(download_config.convert or "webm>mp4")
                    on_state("remux")

                    if full_stream.subtitles:
                        pp.embed_subtitles(full_stream.subtitles)
                        on_state("embed_subtitles")
                elif download_config.type == "audio" and audio_format:
                    if (
                        download_config.convert
                        and download_config.convert != audio_format.extension
                    ):
                        pp.remux(download_config.convert)
                        on_state("remux")

                if full_stream.thumbnails:
                    best_thumb = full_stream.thumbnails[-1]
                    pp.embed_thumbnail(best_thumb, square=full_stream.is_music)
                    on_state("embed_thumbnail")

                pp.embed_metadata(full_stream, full_stream.is_music)
                on_state("embed_metadata")

                downloaded_file = pp.filepath

            # Add extension to filepath
            output = output.parent / f"{output.name}{downloaded_file.suffix}"

            # STATUS: Finish
            output.parent.mkdir(parents=True, exist_ok=True)
            output = Path(shutil.move(downloaded_file, output))

            on_progress(CompletedState(id=stream.id, filepath=output))

            return output
        except ConnectionError as e:
            error = DownloadError(str(e))
            on_progress(ErrorState(id=stream.id, message=str(error)))
            raise error

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


def _log_download(stream: LazyStream, format: Format):
    type = "video" if isinstance(format, VideoFormat) else "audio"
    text = f'Downloading {type} format "{format.id}" (extension:{format.extension} | quality:{format.display_quality})'
    _log_stream(stream, text)


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
