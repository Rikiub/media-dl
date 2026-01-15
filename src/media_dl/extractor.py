"""Raw info extractor."""

from loguru import logger

from media_dl.cache import load_info, save_info
from media_dl.models.content.list import Playlist, Search
from media_dl.models.content.media import Media
from media_dl.models.content.types import ExtractAdapter
from media_dl.ydl.extractor import SEARCH_SERVICE, extract_info, extract_query


def extract_url(url: str, use_cache: bool = True) -> Media | Playlist:
    """Extract info from URL."""

    logger.debug("Extract URL: {url}", url=url)

    # Load from cache
    if json := use_cache and load_info(url):
        return ExtractAdapter.validate_json(json, by_alias=True)

    # Extract info
    info = extract_info(url)
    result = ExtractAdapter.validate_python(info, by_alias=True)

    # Save to cache
    if use_cache:
        save_info(result.url, result.to_ydl_json())

    return result


def extract_search(
    query: str,
    service: SEARCH_SERVICE,
    limit: int = 20,
    use_cache: bool = True,
) -> Search:
    """Extract info from search provider."""

    logger.debug(
        'Search from "{service}": "{query}".',
        service=service,
        query=query,
    )

    # Load from cache
    if json := use_cache and load_info(query):
        return Search.from_ydl_json(json)

    # Extract info
    info = extract_query(query, service, limit)
    result = Search(query=query, service=service, **info)

    # Save to cache
    if use_cache:
        save_info(result.query, result.to_ydl_json())

    return result
