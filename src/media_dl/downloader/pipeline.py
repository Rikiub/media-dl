import shutil
from contextlib import contextmanager
from pathlib import Path

from loguru import logger
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessorError

from media_dl.downloader.config import FormatConfig
from media_dl.downloader.selector import FormatSelector
from media_dl.downloader.states.debug import debug_callback
from media_dl.exceptions import DownloadError
from media_dl.models.formats.types import AudioFormat, Format, VideoFormat
from media_dl.models.list import LazyPlaylist
from media_dl.models.progress.format import FormatState
from media_dl.models.progress.processor import ProcessorType
from media_dl.models.progress.states import (
    CompletedState,
    DownloadingState,
    ErrorState,
    ExtractingState,
    MergingState,
    ProcessingState,
    ProgressDownloadCallback,
    ResolvedState,
    SkippedState,
)
from media_dl.models.stream import LazyStream, Stream
from media_dl.path import get_tempfile
from media_dl.postprocessor import PostProcessor
from media_dl.template.parser import generate_output_template
from media_dl.ydl.types import SupportedExtensions, ThumbnailSupport


class DownloadPipeline:
    """Handles the lifecycle of a single stream download."""

    def __init__(
        self,
        config: FormatConfig,
        stream: LazyStream,
        playlist: LazyPlaylist | None = None,
        on_progress: ProgressDownloadCallback | None = None,
        cache: bool = True,
    ):
        self.id = stream.id
        self.stream = stream
        self.playlist = playlist
        self.config = config
        self.cache = cache

        if on_progress:
            self.progress = lambda state: [
                f(state) for f in (on_progress, debug_callback)
            ]
        else:
            self.progress = lambda d: None

        # Internal State
        self.audio_bytes = 0
        self.video_bytes = 0

        logger.debug(self.config)

    def run(self) -> Path:
        try:
            return self._worker()
        except ConnectionError as e:
            self.progress(ErrorState(id=self.id, message=str(e)))
            raise DownloadError(str(e))

    def _worker(self):
        self.progress(ExtractingState(id=self.id, stream=self.stream))

        # 1. Resolve Data
        stream = self.stream.resolve(self.cache)
        playlist = self.playlist.resolve() if self.playlist else None

        self.progress(ResolvedState(id=self.id, stream=stream))

        # 2. Select Formats
        video_fmt, audio_fmt = FormatSelector(self.config).resolve(stream)

        # 3. Calculate Path & Check Existence
        output = str(self.config.output)

        if self.config.output.is_dir():
            # Default template
            output = output + "/" + "{uploader} - {title}"

        output = generate_output_template(
            output,
            stream=stream,
            playlist=playlist,
            format=video_fmt or audio_fmt,
        )

        if duplicate := self._check_exists(output):
            self.progress(SkippedState(id=self.id, filepath=duplicate))
            return duplicate

        # 4. Download
        downloaded_file = self._download_formats(video_fmt, audio_fmt)

        # 5. Post-Process
        downloaded_file = self._postprocess(
            stream,
            downloaded_file,
            video_fmt or audio_fmt,
        )

        # 6. Finalize (Move to target)
        return self._move_to_final(downloaded_file, output)

    def _download_formats(
        self,
        video_fmt: VideoFormat | None = None,
        audio_fmt: AudioFormat | None = None,
    ) -> Path:
        """Orchestrates the physical download of bytes."""

        state = DownloadingState(id=self.id)
        state.total_bytes = sum(f.filesize or 0 for f in [video_fmt, audio_fmt] if f)

        video_file = None
        audio_file = None

        self.video_bytes = 0
        self.audio_bytes = 0

        def _update_progress(fmt_state: FormatState, is_video: bool):
            if is_video:
                self.video_bytes = fmt_state.downloaded_bytes
            else:
                self.audio_bytes = fmt_state.downloaded_bytes

            state.downloaded_bytes = self.video_bytes + self.audio_bytes
            state.speed = fmt_state.speed
            state.elapsed = fmt_state.elapsed

            self.progress(state)

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

            pp = PostProcessor.from_formats_merge(
                f"{get_tempfile()}.{extension}",
                formats=[(video_fmt, video_file), (audio_fmt, audio_file)],
                ffmpeg_path=self.config.ffmpeg_path,
            )

            self.progress(
                MergingState(
                    id=self.id,
                    video_format=video_fmt,
                    audio_format=audio_fmt,
                )
            )

            return pp.filepath
        elif video_file:
            return video_file
        elif audio_file:
            return audio_file
        else:
            raise DownloadError("Formats not founded.")

    def _postprocess(
        self,
        stream: Stream,
        filepath: Path,
        format: Format | None = None,
    ):
        if not self.config.ffmpeg_path:
            return filepath

        pp = PostProcessor(filepath, self.config.ffmpeg_path)

        @contextmanager
        def track_pp(name: ProcessorType):
            state = ProcessingState(
                id=self.id,
                filepath=pp.filepath,
                stage="started",
                processor=name,
            )
            self.progress(state)

            try:
                yield
            finally:
                state.stage = "completed"
                state.filepath = pp.filepath
                self.progress(state)

        with track_pp("starting"):
            pass

        # Remuxing
        if isinstance(format, VideoFormat):
            with track_pp("change_container"):
                pp.change_container(self.config.convert or "mp4")

            if stream.subtitles:
                with track_pp("embed_subtitles"):
                    pp.embed_subtitles(stream.subtitles)

        elif isinstance(format, AudioFormat):
            if self.config.convert and self.config.convert != format.extension:
                try:
                    with track_pp("change_container"):
                        pp.change_container(self.config.convert)
                except FFmpegPostProcessorError:
                    with track_pp("convert_audio"):
                        pp.convert_audio(self.config.convert)

        # Metadata
        if stream.thumbnails:
            if pp.filepath.suffix[1:] in ThumbnailSupport:
                with track_pp("embed_thumbnail"):
                    pp.embed_thumbnail(stream.thumbnails[-1], square=stream.is_music)

        if self.config.embed_metadata:
            with track_pp("embed_metadata"):
                pp.embed_metadata(stream, stream.is_music)

        return pp.filepath

    def _check_exists(self, output: Path) -> Path | None:
        for path in output.parent.iterdir():
            if path.is_file() and path.stem == output.name:
                extension = path.suffix[1:]

                if (
                    self.config.type == "video"
                    and extension in SupportedExtensions.video
                    or self.config.type == "audio"
                    and extension in SupportedExtensions.audio
                ):
                    return path

    def _move_to_final(self, src: Path, dest: Path) -> Path:
        final_path = dest.parent / f"{dest.name}{src.suffix}"
        final_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(src, final_path)
        self.progress(CompletedState(id=self.id, filepath=final_path))

        return final_path
