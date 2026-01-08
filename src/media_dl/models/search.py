from typing_extensions import Self

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
        info = extract_search(query, provider, limit)
        return cls(query=query, provider=provider, **info)
