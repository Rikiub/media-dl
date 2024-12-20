"""Raw info extractor."""

import logging
from typing import cast

from yt_dlp import DownloadError
from yt_dlp.networking.exceptions import RequestError

from media_dl._ydl import YTDLP, format_except_message
from media_dl.exceptions import ExtractError
from media_dl.extractor.helper import is_playlist, is_stream
from media_dl.types import SEARCH_PROVIDER, InfoDict

log = logging.getLogger(__name__)


def extract_search(query: str, provider: SEARCH_PROVIDER, limit: int = 20) -> InfoDict:
    """Extract info from search provider."""

    match provider:
        case "youtube":
            prov = f"ytsearch{limit}:"
        case "ytmusic":
            prov = "https://music.youtube.com/search?q="
        case "soundcloud":
            prov = f"scsearch{limit}:"
        case _:
            raise ValueError(f"{provider} is invalid. Should be: {SEARCH_PROVIDER}")

    log.debug('Search from "%s": "%s".', provider, query)
    return _fetch_query(prov + query)


def extract_url(url: str) -> InfoDict:
    """Extract info from URL."""

    log.debug("Extract URL: %s", url)
    return _fetch_query(url)


def _fetch_query(query: str) -> InfoDict:
    """Base info dict extractor."""

    try:
        ydl = YTDLP(
            {
                "extract_flat": "in_playlist",
                "skip_download": True,
            }
        )
        info = ydl.extract_info(query, download=False)
        info = cast(InfoDict, info)
    except (DownloadError, RequestError) as err:
        msg = format_except_message(err)
        raise ExtractError(msg)

    # Some extractors need redirect to "real URL" (Example: Pinterest)
    # In this case, we need do another request.
    if info["extractor_key"] == "Generic" and info["url"] != query:
        return _fetch_query(info["url"])

    if not (is_playlist(info) or is_stream(info)):
        raise ExtractError(f"{query} return nothing.")

    return info
