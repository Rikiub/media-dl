from pathlib import Path

from media_dl.extractor import SEARCH_PROVIDER, InfoExtractor

from media_dl.download.downloader import Downloader
from media_dl.download.config import StrPath, FormatConfig, FILE_REQUEST
from media_dl.models import ExtractResult, Playlist, Stream, Format
from media_dl import helper


class MediaDL:
    """Media-DL API. Handler for URLs extraction, serialization and streams download.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: Target file format to search or convert if is a extension.
        quality: Target quality to try filter.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable. By default, it'll try get the global installed FFmpeg.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
        remux: If format extension not specified, will convert to most compatible extension when necessary. (FFmpeg)

    Raises:
        FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
    """

    def __init__(
        self,
        format: FILE_REQUEST = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        ffmpeg: StrPath | None = None,
        metadata: bool = True,
        remux: bool = True,
        threads: int = 4,
        quiet: bool = False,
    ):
        self.downloader_config = FormatConfig(
            format=format,
            quality=quality,
            output=output,
            ffmpeg=ffmpeg,
            metadata=metadata,
            remux=remux,
        )

        self._downloader = Downloader(
            format_config=self.downloader_config,
            max_threads=threads,
            render_progress=not quiet,
        )
        self._extr = InfoExtractor()

    def extract_url(self, url: str) -> Stream | Playlist:
        """Extract and serialize information from URL.

        Returns:
            - Single `Stream`.
            - `Playlist` with multiple `Streams`.

        Raises:
            ExtractionError: Something bad happens when try extract the URL.
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
        """Extract and serialize information from search provider.

        Returns:
            List of streams founded in the search
            (Streams will be incomplete).

        Raises:
            ExtractionError: Something bad happens when try extract the query.
        """

        info = self._extr.extract_search(query, provider)
        return [Stream._from_info(entry) for entry in info["entries"]]

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
