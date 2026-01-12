"""Raw info extractor."""

from loguru import logger

from media_dl.exceptions import ExtractError
from media_dl.ydl.extractor import SEARCH_SERVICE, extract_info, extract_query
from media_dl.ydl.types import YDLExtractInfo

PLAYLISTS_EXTRACTORS = ["YoutubeTab"]


def extract_search(
    query: str,
    service: SEARCH_SERVICE,
    limit: int = 20,
) -> YDLExtractInfo:
    """Extract info from search provider."""

    logger.debug(
        'Search from "{service}": "{query}".',
        service=service,
        query=query,
    )

    info = extract_query(query, service, limit)
    info = _validate_info(info)
    return info


def extract_url(url: str) -> YDLExtractInfo:
    """Extract info from URL."""

    logger.debug("Extract URL: {url}", url=url)

    info = extract_info(url)
    info = _validate_info(info)
    return info


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


def _validate_info(info: YDLExtractInfo) -> YDLExtractInfo:
    """Base info dict extractor."""

    if not (is_playlist(info) or is_stream(info)):
        raise ExtractError(f"{info['url']} returned nothing.")

    return info
