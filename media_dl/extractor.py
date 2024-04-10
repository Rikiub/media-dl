"""
Raw info extractor.

Should be used as module, example:

>>> from media_dl import extractor
>>> url = "https://www.youtube.com/watch?v=BaW_jenozKc"
>>> extractor.from_url(url)

For searching:

>>> extractor.from_search("Sub Urban - Cradles", provider="ytmusic")
"""

from typing import cast, Literal
import logging

from yt_dlp import DownloadError

from media_dl.exceptions import ExtractError
from media_dl.helper import InfoDict, YTDLP, better_exception_msg

log = logging.getLogger(__name__)

SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]


def from_url(url: str) -> InfoDict:
    """Extract info from URL."""

    log.debug("Extracting: %s", url)

    if info := _fetch_query(url):
        return info
    else:
        raise ExtractError("Unable to extract.", url)


def from_search(query: str, provider: SEARCH_PROVIDER) -> InfoDict:
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

    log.debug('Searching "%s" from "%s".', query, provider)

    if info := _fetch_query(prov + query):
        return info
    else:
        return InfoDict({})


def _fetch_query(query: str) -> InfoDict | None:
    """Base info dict extractor."""

    try:
        info = YTDLP.extract_info(query, download=False)
    except DownloadError as err:
        msg = better_exception_msg(str(err))
        raise ExtractError(msg)
    else:
        info = cast(InfoDict, info)

    if not info:
        return None

    # Some extractors need redirect to "real URL" (Pinterest)
    # For this extractors we need do another request.
    if info["extractor_key"] == "Generic" and info["url"] != query:
        log.debug("Re-fetching %s", query)
        return _fetch_query(info["url"])

    # Check if is a valid playlist and validate
    if entries := info.get("entries"):
        for index, item in enumerate(entries):
            # If item has not the 2 required fields, will be deleted.
            if not (item.get("ie_key") and item.get("id")):
                del entries[index]

        if not entries:
            log.debug("Not founded valid entries in %s.", query)
            return None

        info["entries"] = entries
    # Check if is a single item and save.
    elif info.get("formats"):
        pass
    else:
        return None

    return info
