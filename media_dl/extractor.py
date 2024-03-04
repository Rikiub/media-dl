from typing import cast, Literal
import logging

from yt_dlp import YoutubeDL, DownloadError

from media_dl.ydl_base import InfoDict, better_exception_msg, BASE_OPTS, EXTRACT_OPTS

log = logging.getLogger(__name__)

SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]


class ExtractionError(Exception):
    pass


class InfoExtractor:
    def __init__(self):
        opts = BASE_OPTS | EXTRACT_OPTS
        self.yt_dlp = YoutubeDL(opts)

    def extract_url(self, url: str) -> InfoDict:
        """Extract info from URL."""

        if info := self._fetch_query(url):
            return info
        else:
            raise ExtractionError("Unable to extract", url)

    def extract_search(self, query: str, provider: SEARCH_PROVIDER) -> InfoDict:
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
                raise ValueError(provider, "is invalid. Must be:", SEARCH_PROVIDER)

        if info := self._fetch_query(prov + query):
            return info
        else:
            return InfoDict({})

    def _fetch_query(self, query: str) -> InfoDict | None:
        """Base info dict extractor."""

        try:
            info = self.yt_dlp.extract_info(query, download=False)
        except DownloadError as err:
            msg = better_exception_msg(str(err), query)
            log.debug(msg)
            raise ExtractionError(msg)
        else:
            info = cast(InfoDict, info)

        if not info:
            return None

        # Some extractors redirect the URL to the "real URL",
        # For this extractors we need do another request.
        if info["extractor_key"] == "Generic" and info["url"] != query:
            log.debug("Re-fetching %s", query)
            return self._fetch_query(info["url"])

        # Check if is a valid playlist and validate
        if entries := info.get("entries"):
            for index, item in enumerate(entries):
                # If item has not the 2 required fields, will be deleted.
                if not (item.get("ie_key") and item.get("id")):
                    del entries[index]

            if not entries:
                log.debug("Not founded valid entries in %s", query)
                return None

            info["entries"] = entries
        # Check if is a single item and save.
        elif info.get("formats"):
            pass
        else:
            return None

        return info
