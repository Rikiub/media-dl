from pathlib import Path

from media_dl import extractor
from media_dl.extractor import SEARCH_PROVIDER

from media_dl.download.handler import Downloader as _Downloader
from media_dl.download.config import StrPath, FormatConfig, FILE_REQUEST
from media_dl.models import ExtractResult, Playlist, Stream, Format
from media_dl import helper


def extract_url(url: str) -> Stream | Playlist:
    """Extract and serialize information from URL.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        ExtractionError: Something bad happens when try extract the URL.
    """

    info = extractor.from_url(url)

    if helper.info_is_playlist(info):
        return Playlist._from_info(info)
    elif helper.info_is_single(info):
        return Stream._from_info(info)
    else:
        raise TypeError(url, "unsupported.")


def extract_search(query: str, provider: SEARCH_PROVIDER) -> list[Stream]:
    """Extract and serialize information from search provider.

    Returns:
        List of streams founded in the search
        (Streams will be incomplete).

    Raises:
        ExtractionError: Something bad happens when try extract the query.
    """

    info = extractor.from_search(query, provider)
    return [Stream._from_info(entry) for entry in info["entries"]]


class Downloader:
    def __init__(
        self,
        format: FILE_REQUEST = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        ffmpeg: StrPath | None = None,
        metadata: bool = True,
        threads: int = 4,
        quiet: bool = False,
    ):
        """Streams downloader.

        If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

        Args:
            format: File format to search or convert if is a extension.
            quality: Quality to filter.
            output: Directory where to save files.
            ffmpeg: Path to FFmpeg executable. By default, it will try get the global installed FFmpeg.
            metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)

        Raises:
            FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
        """

        self.downloader_config = FormatConfig(
            format=format,
            quality=quality,
            output=output,
            ffmpeg=ffmpeg,
            metadata=metadata,
        )
        self._downloader = _Downloader(
            format_config=self.downloader_config,
            max_threads=threads,
            render_progress=not quiet,
        )

    def download_single(self, stream: Stream, format: Format | None = None) -> Path:
        """Download a single `Stream` formatted by instance options.

        Args:
            stream: Target `Stream` to download.
            format: Specific `Stream` format to download. By default will select the BEST format.

        Returns:
            Path to downloaded file.

        Raises:
            DownloaderError: Something bad happens when try download.
            ValueError: Provided `Format` wasn't founded in `Stream`.
        """

        return self._downloader.download_single(stream, format)

    def download_multiple(self, data: ExtractResult) -> list[Path]:
        """Download one or more results formatted by instance options.

        Returns:
            List of paths to downloaded files.

        Raises:
            DownloaderError: Something bad happens when try download.
        """

        return self._downloader.download_multiple(data)
