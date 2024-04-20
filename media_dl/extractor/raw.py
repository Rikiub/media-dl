"""Raw info extractor."""

from typing import cast, Literal
import logging

from yt_dlp import DownloadError
from yt_dlp.networking.exceptions import RequestError

from media_dl.exceptions import ExtractError
from media_dl._ydl import InfoDict, YTDLP, format_except_msg

log = logging.getLogger(__name__)

SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]


def from_url(url: str) -> InfoDict:
    """Extract info from URL."""

    log.debug("Extract URL: %s", url)

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

    log.debug('Search from "%s": "%s".', provider, query)

    if info := _fetch_query(prov + query):
        return info
    else:
        return InfoDict({})


def _fetch_query(query: str) -> InfoDict | None:
    """Base info dict extractor."""

    try:
        info = YTDLP.extract_info(query, download=False)
    except (DownloadError, RequestError) as err:
        msg = format_except_msg(err)
        raise ExtractError(msg)

    if info:
        info = cast(InfoDict, info)
    else:
        return None

    # Some extractors need redirect to "real URL" (Example: Pinterest)
    # In this case, we need do another request.
    if info["extractor_key"] == "Generic" and info["url"] != query:
        log.debug("Re-fetching %s", query)
        return _fetch_query(info["url"])

    # Validate playlist
    if entries := info.get("entries"):
        for index, item in enumerate(entries):
            # If item has not the 2 required fields, will be deleted.
            if not (item.get("ie_key") or item.get("extractor_key") and item.get("id")):
                del entries[index]

        if not entries:
            log.debug("Not founded valid entries in %s.", query)
            return None

        info["entries"] = entries
    # Check if is single item
    elif not info.get("formats"):
        return None

    return info
