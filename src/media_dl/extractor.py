"""Raw info extractor."""

from loguru import logger

from media_dl.exceptions import ExtractError
from media_dl.types import SEARCH_PROVIDER
from media_dl.ydl.helpers import extract_info
from media_dl.ydl.types import YDLExtractInfo

PLAYLISTS_EXTRACTORS = ["YoutubeTab"]


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
    return _extract_from_query(prov + query)


def extract_url(url: str) -> YDLExtractInfo:
    """Extract info from URL."""

    logger.debug("Extract URL: {url}", url=url)
    return _extract_from_query(url)


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

    if info.get("ie_key", info.get("extractor_key")) in PLAYLISTS_EXTRACTORS:
        return False
    if info.get("_type") == "url" or info.get("formats"):
        return True

    return False


def _extract_from_query(query: str) -> YDLExtractInfo:
    """Base info dict extractor."""

    info = extract_info(query)

    # Some extractors need redirect to "real URL" (Example: Pinterest)
    # In this case, we need do another request.
    if info.get("extractor_key") == "Generic" and info.get("url") != query:
        if url := info.get("url"):
            return _extract_from_query(url)

    if not (is_playlist(info) or is_stream(info)):
        raise ExtractError(f"{query} return nothing.")

    return info
