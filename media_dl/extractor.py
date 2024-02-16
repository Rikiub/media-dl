from typing import cast
import logging

from yt_dlp import YoutubeDL, DownloadError

from media_dl.types import ydl_opts
from media_dl.types.formats import SEARCH_PROVIDER
from media_dl.types.models import InfoDict, Media, Playlist, ResultType

_supress_logger = logging.getLogger("YoutubeDL")
_supress_logger.disabled = True


class ExtractionError(Exception):
    pass


class InfoExtractor:
    def __init__(self):
        opts = ydl_opts.BASE_OPTS | ydl_opts.EXTRACT_OPTS
        self.yt_dlp = YoutubeDL(opts)

    def _fetch_query(self, query: str) -> InfoDict | None:
        try:
            info = self.yt_dlp.extract_info(query, download=False)
        except DownloadError as err:
            raise ExtractionError(err.msg)
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
        if info := self._fetch_query(url):
            return info
        else:
            return None

    def extract_from_search(self, query: str, provider: SEARCH_PROVIDER) -> InfoDict:
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
    def __init__(self) -> None:
        self._extr = InfoExtractor()

    def _info_to_media(self, info: InfoDict) -> ResultType:
        if info.get("entries"):
            return Playlist.from_info(info)
        else:
            return Media.from_info(info)

    def update_media(self, media: Media) -> tuple[Media, InfoDict]:
        url = media.url
        info = self._extr.extract_from_url(url)

        if info:
            media = Media.from_info(info)
            return (media, info)
        else:
            raise ExtractionError("Failed to fetch data from:", url)

    def extract_from_url(self, url: str) -> ResultType | None:
        if info := self._extr.extract_from_url(url):
            return self._info_to_media(info)
        else:
            return None

    def extract_from_search(self, query: str, provider: SEARCH_PROVIDER) -> list[Media]:
        info = self._extr.extract_from_search(query, provider)
        info = self._info_to_media(info)

        if isinstance(info, Playlist):
            return info.entries
        else:
            return []
