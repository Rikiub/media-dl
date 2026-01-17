import shutil
from contextlib import contextmanager
from pathlib import Path

from loguru import logger
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessorError

from media_dl.downloader.config import FormatConfig
from media_dl.downloader.selector import FormatSelector
from media_dl.downloader.states.debug import debug_callback
from media_dl.exceptions import DownloadError
from media_dl.extractor import MediaExtractor
from media_dl.models.content.media import LazyMedia, Media
from media_dl.models.format.types import AudioFormat, Format, VideoFormat
from media_dl.models.progress.format import FormatState
from media_dl.models.progress.media import (
    CompletedState,
    DownloadingState,
    ErrorState,
    MediaDownloadCallback,
    ResolvedState,
    ResolvingState,
    SkippedState,
)
from media_dl.models.progress.processor import (
    MergingProcessorState,
    ProcessorState,
    ProcessorStateType,
)
from media_dl.path import get_tempfile
from media_dl.processor import MediaProcessor
from media_dl.template.parser import generate_output_template
from media_dl.ydl.types import SupportedExtensions, ThumbnailSupport


class DownloadPipeline:
    """Handles the lifecycle of a single media download."""

    def __init__(
        self,
        media: LazyMedia | Media,
        format_config: FormatConfig | None = None,
        extractor: MediaExtractor | None = None,
        on_progress: MediaDownloadCallback | None = None,
    ):
        self.id = media.id

        self.media = media
        self.config = format_config or FormatConfig("video")
        self.extractor = extractor or MediaExtractor()
        self.progress = lambda d: None

        if on_progress:
            self.progress = lambda state: [
                f(state) for f in (on_progress, debug_callback)
            ]

        logger.debug(self.config)

    def run(self) -> Path:
        # Resolve Data
        media = self.resolve_media()

        # Select Formats
        video_fmt, audio_fmt = FormatSelector(self.config).resolve(media)
        format = video_fmt or audio_fmt

        if not format:
            raise DownloadError("Format not founded")

        #  Calculate Path & Check Existence
        output = generate_output_template(
            self.config.output,
            media,
            format=format,
            default_missing="NA",
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        if duplicate := self.check_output_duplicate(output, format):
            return duplicate

        try:
            # Download File
            downloaded_file = self.download_formats(video_fmt, audio_fmt)

            if self.config.ffmpeg_path:
                # Process File
                downloaded_file = self.process(downloaded_file, media, format)
        except ConnectionError as e:
            self.progress(ErrorState(id=self.id, message=str(e)))
            raise DownloadError(str(e))

        # Complete (Move to target)
        return self.move_to_final(downloaded_file, output)

    def resolve_media(self) -> Media:
        media = self.media

        self.progress(ResolvingState(id=self.id, media=media))

        if not isinstance(media, Media):
            media = self.extractor.resolve(media)

        self.progress(ResolvedState(id=self.id, media=media))
        return media

    def check_output_duplicate(self, output: Path, format: Format) -> Path | None:
        for path in output.parent.iterdir():
            if path.is_file() and path.stem == output.name:
                if (
                    format.extension in SupportedExtensions.video
                    or format.extension in SupportedExtensions.audio
                ):
                    self.progress(SkippedState(id=self.id, filepath=path))
                    return path

    def download_formats(
        self,
        video_fmt: VideoFormat | None = None,
        audio_fmt: AudioFormat | None = None,
    ) -> Path:
        """Orchestrates the physical download of bytes."""

        downloading = DownloadingState(id=self.id)
        downloading.total_bytes = sum(
            f.filesize or 0 for f in [video_fmt, audio_fmt] if f
        )

        video_file = None
        audio_file = None

        video_bytes = 0
        audio_bytes = 0

        def _update_progress(fmt_state: FormatState, is_video: bool):
            nonlocal video_bytes, audio_bytes

            if is_video:
                video_bytes = fmt_state.downloaded_bytes
            else:
                audio_bytes = fmt_state.downloaded_bytes

            downloading.downloaded_bytes = video_bytes + audio_bytes
            downloading.speed = fmt_state.speed
            downloading.elapsed = fmt_state.elapsed

            self.progress(downloading)

        def _log(format: Format):
            type = "video" if isinstance(format, VideoFormat) else "audio"
            logger.debug(
                'Downloading {type} format "{format_id}" (extension:{extension} | quality:{quality})',
                type=type,
                format_id=format.id,
                extension=format.extension,
                quality=format.quality,
            )

        # Download Audio
        if audio_fmt:
            _log(audio_fmt)
            audio_file = audio_fmt.download(
                get_tempfile(),
                lambda s: _update_progress(s, is_video=False),
            )

        # Download Video
        if video_fmt:
            _log(video_fmt)
            video_file = video_fmt.download(
                get_tempfile(),
                lambda s: _update_progress(s, is_video=True),
            )

        # Merge if necessary
        if (
            self.config.ffmpeg_path
            and (video_file and video_fmt)
            and (audio_file and audio_fmt)
        ):
            extension = self.config.convert or "mp4"
            filepath = Path(f"{get_tempfile()}.{extension}")

            merging = MergingProcessorState(
                id=self.id,
                filepath=filepath,
                stage="started",
                video_format=video_fmt,
                audio_format=audio_fmt,
            )

            prc = MediaProcessor.from_formats_merge(
                filepath,
                formats=[(video_fmt, video_file), (audio_fmt, audio_file)],
                ffmpeg_path=self.config.ffmpeg_path,
            )

            merging.stage = "completed"
            self.progress(merging)

            return prc.filepath
        elif video_file:
            return video_file
        elif audio_file:
            return audio_file
        else:
            raise DownloadError("Formats not founded.")

    def process(
        self,
        filepath: Path,
        media: Media,
        format: Format | None = None,
    ) -> Path:
        prc = MediaProcessor(filepath, self.config.ffmpeg_path)

        @contextmanager
        def track_prc(name: ProcessorStateType):
            state = ProcessorState(
                id=self.id,
                filepath=prc.filepath,
                stage="started",
                processor=name,
            )
            self.progress(state)

            try:
                yield
                state.stage = "completed"
                state.filepath = prc.filepath
                self.progress(state)
            except Exception:
                raise

        # Remuxing
        if isinstance(format, VideoFormat):
            with track_prc("change_container"):
                prc.change_container(self.config.convert or "mp4")

            if media.subtitles:
                with track_prc("embed_subtitles"):
                    subtitles = media.subtitles.download(get_tempfile())
                    prc.embed_subtitles(subtitles)

        elif isinstance(format, AudioFormat):
            if self.config.convert and self.config.convert != format.extension:
                try:
                    with track_prc("change_container"):
                        prc.change_container(self.config.convert)
                except FFmpegPostProcessorError:
                    with track_prc("convert_audio"):
                        prc.convert_audio(self.config.convert)

        # Metadata
        if media.thumbnails:
            if prc.filepath.suffix[1:] in ThumbnailSupport:
                with track_prc("embed_thumbnail"):
                    thumbnail = media.thumbnails[-1].download(get_tempfile())
                    prc.embed_thumbnail(thumbnail, square=media.is_music)

        if self.config.embed_metadata:
            with track_prc("embed_metadata"):
                prc.embed_metadata(media, media.is_music)

        return prc.filepath

    def move_to_final(self, src: Path, dest: Path) -> Path:
        final_path = dest.parent / f"{dest.name}{src.suffix}"
        final_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(src, final_path)
        self.progress(CompletedState(id=self.id, filepath=final_path))

        return final_path
