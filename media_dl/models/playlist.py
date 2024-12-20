from __future__ import annotations

from typing import Annotated

from pydantic import Field

from media_dl.extractor.info import extract_search
from media_dl.models.base import ExtractID
from media_dl.models.metadata import Thumbnail
from media_dl.models.stream import LazyStream
from media_dl.types import SEARCH_PROVIDER


class BaseList:
    streams: Annotated[list[LazyStream], Field(alias="entries")]


class Playlist(BaseList, ExtractID):
    title: str
    thumbnails: list[Thumbnail] = []


class SearchQuery(BaseList):
    def __init__(self, query: str, provider: SEARCH_PROVIDER, limit: int = 20):
        info = extract_search(query, provider, limit)

        self.extractor: str = info["extractor_key"]
        self.query: str = query
        self.streams = [LazyStream(**s) for s in info["entries"]]
