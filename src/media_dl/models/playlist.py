from __future__ import annotations

import json
from typing import Annotated

from pydantic import AliasChoices, Field, OnErrorOmit

from media_dl.extractor import extract_search, is_playlist, is_stream
from media_dl.models.base import URL_TYPE, ExtractID
from media_dl.models.metadata import Thumbnail
from media_dl.models.stream import LazyStream
from media_dl.types import SEARCH_PROVIDER


class LazyPlaylist(ExtractID):
    url: Annotated[
        str, Field(alias="playlist_url", validation_alias=AliasChoices(*URL_TYPE))
    ]
    id: Annotated[str, Field(alias="playlist_id", validation_alias="id")]
    title: Annotated[str, Field(alias="playlist_title", validation_alias="title")] = ""
    uploader: str | None = None
    thumbnails: list[Thumbnail] = []
    streams: Annotated[
        list[OnErrorOmit[LazyStream]],
        Field(validation_alias="entries"),
    ] = []
    playlists: Annotated[
        list[OnErrorOmit[LazyPlaylist]],
        Field(validation_alias="entries"),
    ] = []

    def fetch(self) -> Playlist:
        """Fetch real playlist.

        Returns:
            Updated version of self Playlist.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        return Playlist.from_url(self.url)


class Playlist(LazyPlaylist): ...


class SearchQuery:
    streams: list[LazyStream] = []
    playlists: list[LazyPlaylist] = []

    def __init__(self, query: str, provider: SEARCH_PROVIDER, limit: int = 20):
        info = extract_search(query, provider, limit)

        try:
            extractor: str = info["extractor_key"]
            entries: list[dict] = info["entries"]
        except IndexError:
            raise ValueError()

        self.extractor: str = extractor
        self.query: str = query

        for entry in entries:
            if is_playlist(entry):
                self.playlists.append(LazyPlaylist(**entry))
            elif is_stream(entry):
                self.streams.append(LazyStream(**entry))

    def model_dump_json(self) -> str:
        return json.dumps(self.__dict__)

    def __rich_repr__(self):
        yield "extractor", self.extractor
        yield "query", self.query
        yield "streams", self.streams
