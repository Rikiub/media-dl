from __future__ import annotations

from typing import Annotated

from pydantic import AliasChoices, Field

from media_dl.extractor import extract_search
from media_dl.models.base import URL_TYPE, ExtractID
from media_dl.models.metadata import Thumbnail
from media_dl.models.stream import LazyStream
from media_dl.types import SEARCH_PROVIDER


class BaseList:
    streams: Annotated[list[LazyStream], Field(validation_alias="entries")]


class Playlist(BaseList, ExtractID):
    url: Annotated[
        str, Field(alias="playlist_url", validation_alias=AliasChoices(*URL_TYPE))
    ]
    id: Annotated[str, Field(alias="playlist_id", validation_alias="id")]
    title: Annotated[str, Field(alias="playlist_title", validation_alias="title")]
    uploader: str | None = None
    thumbnails: list[Thumbnail] = []


class SearchQuery(BaseList):
    def __init__(self, query: str, provider: SEARCH_PROVIDER, limit: int = 20):
        info = extract_search(query, provider, limit)

        try:
            extractor = info["extractor_key"]
            entries = info["entries"]
        except IndexError:
            raise ValueError()

        self.extractor: str = extractor
        self.query: str = query
        self.streams = [LazyStream(**s) for s in entries]
