"""Raw info extractor."""

from typing import cast

from loguru import logger
from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import DownloadError

from media_dl.exceptions import ExtractError
from media_dl.types import SEARCH_PROVIDER
from media_dl.ydl.messages import format_except_message
from media_dl.ydl.types import YDLExtractInfo
from media_dl.ydl.wrapper import YTDLP

PLAYLISTS_EXTRACTORS = ["YoutubeTab"]


def is_playlist(info: YDLExtractInfo) -> bool:
    """Check if info is a playlist."""

    if (
        info.get("_type") == "playlist"
        or info.get("ie_key") in PLAYLISTS_EXTRACTORS
        or info.get("entries")
    ):
        return True
    else:
        return False


def is_stream(info: YDLExtractInfo) -> bool:
    """Check if info is a single Stream."""

    if info.get("ie_key") or info.get("extractor_key") in PLAYLISTS_EXTRACTORS:
        return False
    if info.get("_type") == "url" or info.get("formats"):
        return True

    return False


def extract_search(
    query: str, provider: SEARCH_PROVIDER, limit: int = 20
) -> YDLExtractInfo:
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

    logger.debug(
        'Search from "{provider}": "{query}".',
        provider=provider,
        query=query,
    )
    return _fetch_query(prov + query)


def extract_url(url: str) -> YDLExtractInfo:
    """Extract info from URL."""

    logger.debug("Extract URL: {url}", url=url)
    return _fetch_query(url)


def _fetch_query(query: str) -> YDLExtractInfo:
    """Base info dict extractor."""

    try:
        ydl = YTDLP(
            {
                "extract_flat": "in_playlist",
                "skip_download": True,
            }
        )
        info = ydl.extract_info(query, download=False)
        info = cast(YDLExtractInfo, info)
    except (DownloadError, RequestError) as err:
        msg = format_except_message(err)
        raise ExtractError(msg)

    # Some extractors need redirect to "real URL" (Example: Pinterest)
    # In this case, we need do another request.
    if info.get("extractor_key") == "Generic" and info.get("url") != query:
        if url := info.get("url"):
            return _fetch_query(url)

    if not (is_playlist(info) or is_stream(info)):
        raise ExtractError(f"{query} return nothing.")

    return info
