"""Raw info extractor."""

from typing import overload
from loguru import logger

from media_dl.cache import load_info, save_info
from media_dl.models.content.list import LazyPlaylist, Playlist, Search
from media_dl.models.content.media import LazyMedia, Media
from media_dl.models.content.types import ExtractAdapter
from media_dl.types import StrUrl
from media_dl.ydl.extractor import SEARCH_SERVICE, extract_info, extract_query


class MediaExtractor:
    def __init__(self, use_cache: bool = True) -> None:
        self.use_cache = use_cache

    @overload
    def resolve(self, item: LazyMedia) -> Media: ...

    @overload
    def resolve(self, item: LazyPlaylist) -> Playlist: ...

    def resolve(self, item: LazyMedia | LazyPlaylist):
        return self.extract_url(str(item.url))

    def extract_url(self, url: StrUrl) -> Media | Playlist:
        """Extract media from URL."""

        url = str(url)
        logger.debug("Extract URL: {url}", url=url)

        # Load from cache
        if json := self.use_cache and load_info(url):
            return ExtractAdapter.validate_json(json, by_alias=True)

        # Extract info
        info = extract_info(url)
        result = ExtractAdapter.validate_python(info, by_alias=True)

        # Save to cache
        if self.use_cache:
            save_info(str(result.url), result.to_ydl_json())

        return result

    def extract_search(
        self,
        query: str,
        service: SEARCH_SERVICE,
        limit: int = 20,
    ) -> Search:
        """Extract media from search provider."""

        logger.debug(
            'Search from "{service}": "{query}".',
            service=service,
            query=query,
        )

        # Load from cache
        if json := self.use_cache and load_info(query):
            return Search.from_ydl_json(json)

        # Extract info
        info = extract_query(query, service, limit)
        result = Search(query=query, service=service, **info)

        # Save to cache
        if self.use_cache:
            save_info(result.query, result.to_ydl_json())

        return result
