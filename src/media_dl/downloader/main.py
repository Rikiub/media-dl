from pathlib import Path

from media_dl.downloader.config import DEFAULT_OUTPUT_TEMPLATE, FormatConfig
from media_dl.downloader.states.progress import ProgressCallback
from media_dl.downloader.type.bulk import DownloadBulk
from media_dl.extractor import MediaExtractor
from media_dl.models.content.list import MediaList
from media_dl.models.content.media import LazyMedia
from media_dl.models.content.types import ExtractResult, MediaListEntries
from media_dl.models.progress.list import PlaylistDownloadCallback
from media_dl.models.progress.media import MediaDownloadCallback
from media_dl.types import FILE_FORMAT, StrPath

_MediaResult = ExtractResult | MediaListEntries
MediaResult = MediaList | _MediaResult | list[LazyMedia]

# Import default callback if rich is installed.
try:
    _progress = ProgressCallback()
    _on_progress = _progress.callback_media
    _on_playlist = _progress.callback_playlist
except ImportError:
    _on_progress = lambda v: None  # noqa: E731
    _on_playlist = lambda v: None  # noqa: E731


class MediaDownloader:
    def __init__(
        self,
        format: FILE_FORMAT = "video",
        quality: int | None = None,
        output: StrPath = DEFAULT_OUTPUT_TEMPLATE,
        threads: int = 4,
        ffmpeg_path: StrPath | None = None,
        embed_metadata: bool = True,
        extractor: MediaExtractor | None = None,
    ):
        """Multi-thread media downloader.

        If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

        Args:
            format: File format to search or convert with (FFmpeg) if is a extension.
            quality: Quality to filter.
            output: Directory where to save files.
            threads: Maximum processes to execute.
            ffmpeg_path: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
            embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)

        Raises:
            FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
        """

        self.config = FormatConfig(
            format=format,
            quality=quality,
            output=output,
            ffmpeg_path=ffmpeg_path,
            embed_metadata=embed_metadata,
        )
        self.extractor = extractor
        self.threads = threads

    def download(
        self,
        media: LazyMedia,
        on_progress: MediaDownloadCallback | None = _on_progress,
    ) -> Path:
        """Single download a `Media` result.

        Args:
            media: Target `Media` to download.
            on_progress: Callback function to get progress information.

        Returns:
            Path to downloaded file.
        """

        pipeline = DownloadBulk(
            media,
            format_config=self.config,
            extractor=self.extractor,
            on_progress=on_progress,
        )
        paths = pipeline.run()
        return paths[0]

    def download_all(
        self,
        data: MediaResult,
        on_progress: MediaDownloadCallback | None = _on_progress,
        on_playlist: PlaylistDownloadCallback | None = _on_playlist,
    ) -> list[Path]:
        """Batch download any result.

        Returns:
            List of paths to downloaded files.
        """

        return DownloadBulk(
            data,
            self.config,
            self.extractor,
            self.threads,
            on_progress,
            on_playlist,
        ).run()
