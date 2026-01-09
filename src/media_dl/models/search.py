from typing_extensions import Self

from media_dl.cache import load_info, save_info
from media_dl.extractor import extract_search
from media_dl.models.base import BaseDataList, ExtractorKey
from media_dl.models.playlist import LazyPlaylists
from media_dl.models.stream import LazyStreams
from media_dl.types import SEARCH_PROVIDER


class Search(BaseDataList):
    extractor: ExtractorKey

    query: str = ""
    provider: str = ""

    streams: LazyStreams = []
    playlists: LazyPlaylists = []

    @classmethod
    def from_query(cls, query: str, provider: SEARCH_PROVIDER, limit: int = 20) -> Self:
        # Load from cache
        if info := load_info(query):
            return cls.model_validate_json(info)

        # Fetch info
        info = extract_search(query, provider, limit)
        cls = cls(query=query, provider=provider, **info)

        # Save to cache
        save_info(cls.query, cls.as_ydl_json())
        return cls
