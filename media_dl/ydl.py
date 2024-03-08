from pathlib import Path

from media_dl.extractor import SEARCH_PROVIDER, InfoExtractor

from media_dl.download.downloader import Downloader
from media_dl.download.config import StrPath, FormatConfig, FILE_REQUEST
from media_dl.models import ExtractResult, Playlist, Stream, Format
from media_dl import helper


__all__ = ["YDL"]


class YDL:
    """Media-DL API

    Handler for URLs extraction, serialization and streams download.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: Target file format to search or convert if is a extension.
        quality: Target quality to filter.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
        remux: If format extension not specified, will convert to most compatible extension when necessary. (FFmpeg)
    """

    def __init__(
        self,
        format: FILE_REQUEST = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        ffmpeg: StrPath = "",
        metadata: bool = True,
        remux: bool = True,
        threads: int = 4,
        quiet: bool = False,
    ):
        self._downloader = Downloader(
            format_config=FormatConfig(
                format=format,
                quality=quality,
                output=output,
                ffmpeg=ffmpeg,
                metadata=metadata,
                remux=remux,
            ),
            max_threads=threads,
            render_progress=not quiet,
        )
        self._extr = InfoExtractor()

    def extract_url(self, url: str) -> Stream | Playlist:
        """Extract and serialize information from URL.

        Returns:
            - Single `Stream`
            - `Playlist` with multiple `Streams`.
        """

        info = self._extr.extract_url(url)

        if helper.is_playlist(info):
            return Playlist._from_info(info)
        elif helper.is_single(info):
            return Stream._from_info(info)
        else:
            raise TypeError(url, "unsupported.")

    def extract_search(
        self,
        query: str,
        provider: SEARCH_PROVIDER,
    ) -> list[Stream]:
        """
        Extract and serialize information from search provider.
        The streams returned will be incomplete.
        """

        info = self._extr.extract_search(query, provider)
        return [Stream._from_info(entry) for entry in info["entries"]]

    def download(self, stream: Stream, format: Format | None = None) -> Path:
        return self._downloader.download(stream, format)

    def download_multiple(self, data: ExtractResult) -> list[Path]:
        return self._downloader.download_multiple(data)
