from pathlib import Path

from media_dl.extractor import SEARCH_PROVIDER, InfoExtractor

from media_dl import ydl_base
from media_dl.download import Downloader, FILE_REQUEST

from media_dl.models import ExtractResult
from media_dl.models.list import Playlist
from media_dl.models.stream import Stream, StreamList
from media_dl.models.format import Format

import logging

log = logging.getLogger(__name__)


class YDL:
    def __init__(
        self,
        format: FILE_REQUEST = "video",
        quality: int | None = None,
        output: Path | str = Path.cwd(),
        ffmpeg_location: Path | str = "",
        embed_metadata: bool = True,
        threads: int = 4,
        quiet: bool = False,
    ):
        self._downloader = Downloader(
            format=format,
            quality=quality,
            output=output,
            ffmpeg_path=ffmpeg_location,
            embed_metadata=embed_metadata,
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

        log.debug("Extracting %s", url)
        info = self._extr.extract_url(url)
        log.debug("Extraction finished")

        if ydl_base.is_playlist(info):
            return Playlist.from_info(info)
        elif ydl_base.is_single(info):
            return Stream.from_info(info)
        else:
            raise TypeError(url, "unsupported.")

    def extract_search(
        self,
        query: str,
        provider: SEARCH_PROVIDER,
    ) -> list[Stream]:
        """Extract and serialize information from search provider."""

        log.debug("Searching '%s' from '%s'", query, provider)
        info = self._extr.extract_search(query, provider)
        log.debug("Search finished")

        return list(Stream.from_info(entry) for entry in info["entries"])

    def download(self, data: ExtractResult | Format) -> None:
        log.debug("Starting download")

        return self._downloader.download(data)
