from pathlib import Path
import shutil

from loguru import logger

from media_dl.downloader.config import FormatConfig
from media_dl.downloader.selector import FormatSelector
from media_dl.exceptions import DownloadError
from media_dl.models.formats.types import AudioFormat, Format, VideoFormat
from media_dl.models.list import LazyPlaylist
from media_dl.models.progress.format import FormatState
from media_dl.models.progress.state import (
    CompletedState,
    DownloadingState,
    ErrorState,
    ExtractingState,
    MergingState,
    ProcessingState,
    ProcessorType,
    ProgressDownloadCallback,
    ResolvedState,
    SkippedState,
)
from media_dl.models.stream import LazyStream, Stream
from media_dl.path import get_tempfile
from media_dl.postprocessor import PostProcessor
from media_dl.template.parser import generate_output_template
from media_dl.ydl.types import SupportedExtensions


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
        self.selector = FormatSelector(config)

        if on_progress:
            self.progress = on_progress
        else:
            self.progress = lambda d: None

        # Internal State
        self.audio_bytes = 0
        self.video_bytes = 0

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
        video_fmt, audio_fmt = self.selector.resolve(stream)

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

        if self._check_exists(output):
            self.progress(SkippedState(id=self.id, filepath=output))
            return output

        # 4. Download
        downloaded_file = self._download_formats(video_fmt, audio_fmt)

        # 5. Post-Process
        downloaded_file = self._postprocess(
            stream,
            downloaded_file,
            video_fmt,
            audio_fmt,
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
        if self.selector.config.type == "video" and video_fmt:
            _log(video_fmt)
            video_file = video_fmt.download(
                get_tempfile(),
                lambda s: _update_progress(s, is_video=True),
            )

        # Merge if necessary
        if (video_file and video_fmt) and (audio_file and audio_fmt):
            self.progress(
                MergingState(
                    id=self.id,
                    video_format=video_fmt,
                    audio_format=audio_fmt,
                )
            )

            pp = PostProcessor.from_formats_merge(
                get_tempfile(),
                merge_format=self.selector.config.convert or "mp4",
                formats=[(video_fmt, video_file), (audio_fmt, audio_file)],
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
        video_fmt: VideoFormat | None = None,
        audio_fmt: AudioFormat | None = None,
    ):
        if not self.config.ffmpeg_path:
            return filepath

        pp = PostProcessor(filepath, self.config.ffmpeg_path)

        def notify(type: ProcessorType):
            self.progress(
                ProcessingState(
                    id=self.id,
                    filepath=pp.filepath,
                    processor=type,
                )
            )

        # Remuxing
        if self.selector.config.type == "video" and video_fmt:
            pp.remux(self.selector.config.convert or "webm>mp4")
            notify("remux")

            if stream.subtitles:
                pp.embed_subtitles(stream.subtitles)
                notify("embed_subtitles")

        elif self.selector.config.type == "audio" and audio_fmt:
            if (
                self.selector.config.convert
                and self.selector.config.convert != audio_fmt.extension
            ):
                pp.remux(self.selector.config.convert)
                notify("remux")

        # Metadata
        if stream.thumbnails:
            pp.embed_thumbnail(stream.thumbnails[-1], square=stream.is_music)
            notify("embed_thumbnail")

        pp.embed_metadata(stream, stream.is_music)
        notify("embed_metadata")

        return pp.filepath

    def _check_exists(self, output: Path) -> bool:
        for path in output.parent.iterdir():
            if path.is_file() and path.stem == output.name:
                extension = path.suffix[1:]

                if (
                    self.selector.config.type == "video"
                    and extension in SupportedExtensions.video
                    or self.selector.config.type == "audio"
                    and extension in SupportedExtensions.audio
                ):
                    return True
        return False

    def _move_to_final(self, src: Path, dest: Path) -> Path:
        final_path = dest.parent / f"{dest.name}{src.suffix}"
        final_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(src, final_path)
        self.progress(CompletedState(id=self.id, filepath=final_path))

        return final_path
