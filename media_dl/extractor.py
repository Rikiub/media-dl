from typing import cast
import logging

from yt_dlp import YoutubeDL, DownloadError

from media_dl.types.models import InfoDict, Media, Playlist, ResultType
from media_dl.types.formats import SEARCH_PROVIDER
from media_dl.types import ydl_opts

_supress_logger = logging.getLogger("YoutubeDL")
_supress_logger.disabled = True


class ExtractionError(Exception):
    pass


def resolve_exception_msg(msg: str, url: str) -> str:
    if "HTTP Error" in msg:
        pass

    elif "Unable to download webpage" in msg:
        msg = "Unable to establish internet connection."

    elif "Unable to download" in msg or "Got error" in msg:
        msg = "Unable to download"

    elif "is not a valid URL" in msg:
        msg = f"{url} is not a valid URL"

    elif "Unsupported URL" in msg:
        msg = f"Unsupported URL: {url}"

    elif "ffmpeg not found" in msg:
        msg = "Unable to process the file"

    elif msg.startswith("ERROR: "):
        msg = msg.strip("ERROR: ")

    return msg


class InfoExtractor:
    def __init__(self):
        opts = ydl_opts.BASE_OPTS | ydl_opts.EXTRACT_OPTS
        self.yt_dlp = YoutubeDL(opts)

    def _fetch_query(self, query: str) -> InfoDict | None:
        """Base info dict extractor."""

        try:
            info = self.yt_dlp.extract_info(query, download=False)
        except DownloadError as err:
            msg = resolve_exception_msg(str(err), query)
            raise ExtractionError(msg)
        else:
            info = cast(InfoDict, info)

        if not info:
            return None

        # Some extractors redirect the URL to the "real URL",
        # For this extractors we need do another request.
        if info["extractor_key"] == "Generic" and info["url"] != query:
            return self._fetch_query(info["url"])

        # Check if is a valid playlist and validate
        if entries := info.get("entries"):
            for index, item in enumerate(entries):
                # If item not has the 2 required fields, will be deleted.
                if not (item.get("ie_key") and item.get("id")):
                    del entries[index]
            if entries:
                info["entries"] = entries
            else:
                return None
        # Check if is a single item and save.
        elif not info.get("formats"):
            return None

        return info

    def extract_from_url(self, url: str) -> InfoDict | None:
        """Extract info from URL."""

        if info := self._fetch_query(url):
            return info
        else:
            return None

    def extract_from_search(self, query: str, provider: SEARCH_PROVIDER) -> InfoDict:
        """Extract info from search provider."""

        search_limit = 20

        match provider:
            case "youtube":
                prov = f"ytsearch{search_limit}:"
            case "ytmusic":
                prov = "https://music.youtube.com/search?q="
            case "soundcloud":
                prov = f"scsearch{search_limit}:"
            case _:
                raise ValueError(f"'{provider}' is invalid.")

        if info := self._fetch_query(prov + query):
            return info
        else:
            return InfoDict({})


class Extractor:
    """Extractor, serializer and handler for `Results`."""

    def __init__(self) -> None:
        self._extr = InfoExtractor()

    def _info_to_media(self, info: InfoDict) -> Media | Playlist:
        """Serialize raw info dict to its appropiate `Media` object"""

        if info.get("entries"):
            return Playlist.from_info(info)
        else:
            return Media.from_info(info)

    @staticmethod
    def resolve_result(data: ResultType) -> list[Media]:
        """Convert any result to generic list for easy iteration."""

        match data:
            case Media():
                return [data]
            case Playlist():
                return data.entries
            case list():
                return data
            case _:
                raise TypeError(data)

    def update_media(self, media: Media) -> tuple[Media, InfoDict]:
        """Create new and complete copy of the provided item. Useful for update `Playlist` entries."""

        url = media.url
        info = self._extr.extract_from_url(url)

        if info:
            media = Media.from_info(info)
            return (media, info)
        else:
            raise ExtractionError("Failed to fetch data from:", url)

    def extract_from_url(self, url: str) -> Media | Playlist | None:
        """Extract and serialize information from URL.

        Returns:
            `Media` or `Playlist` item.

            If return `Playlist`, its entries will be incomplete.
            Use `update_media` function to update its entries.
        """

        if info := self._extr.extract_from_url(url):
            return self._info_to_media(info)
        else:
            return None

    def extract_from_search(self, query: str, provider: SEARCH_PROVIDER) -> list[Media]:
        """Extract and serialize information from search provider."""

        info = self._extr.extract_from_search(query, provider)
        info = self._info_to_media(info)

        if isinstance(info, Playlist):
            return info.entries
        else:
            return []
