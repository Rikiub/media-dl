"""Raw info extractor."""

from typing import cast, Literal
import logging

from yt_dlp import DownloadError
from yt_dlp.networking.exceptions import RequestError

from media_dl._ydl import InfoDict, YTDLP, format_except_msg
from media_dl.exceptions import ExtractError
from media_dl.extractor import serializer

log = logging.getLogger(__name__)

SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]


def extract_url(url: str) -> InfoDict:
    """Extract info from URL."""

    log.debug("Extract URL: %s", url)
    return _fetch_query(url)


def extract_search(query: str, provider: SEARCH_PROVIDER) -> InfoDict:
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
    return _fetch_query(prov + query)


def _fetch_query(query: str) -> InfoDict:
    """Base info dict extractor."""

    try:
        info = YTDLP.extract_info(query, download=False)
        info = cast(InfoDict, info)
    except (DownloadError, RequestError) as err:
        msg = format_except_msg(err)
        raise ExtractError(msg)

    # Some extractors need redirect to "real URL" (Example: Pinterest)
    # In this case, we need do another request.
    if info["extractor_key"] == "Generic" and info["url"] != query:
        return _fetch_query(info["url"])

    if not (serializer.is_playlist(info) or serializer.is_stream(info)):
        raise ExtractError('"%s" return nothing.')

    return info
