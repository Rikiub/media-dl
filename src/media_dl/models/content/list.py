from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import AliasChoices, Field, SkipValidation, computed_field

from media_dl.models.base import Serializable
from media_dl.models.content.base import (
    URL_CHOICES,
    LazyExtract,
    ExtractorField,
    TypeField,
)
from media_dl.models.content.media import LazyMedia
from media_dl.models.content.metadata import Thumbnail


class MediaList(Serializable):
    entries: Entries = []

    @computed_field
    @property
    def medias(self) -> list[LazyMedia]:
        return [item for item in self.entries if item.type == "url"]

    @computed_field
    @property
    def playlists(self) -> list[LazyPlaylist]:
        return [item for item in self.entries if item.type == "playlist"]


class LazyPlaylist(MediaList, LazyExtract["Playlist"]):
    type: Annotated[Literal["playlist"], SkipValidation] = "playlist"

    url: Annotated[
        str,
        Field(
            alias="playlist_url",
            validation_alias=AliasChoices("playlist_url", *URL_CHOICES),
        ),
    ]
    id: Annotated[
        str,
        Field(
            alias="playlist_id",
            validation_alias=AliasChoices("playlist_id", "id"),
        ),
    ]

    title: Annotated[
        str,
        Field(
            alias="playlist_title",
            validation_alias=AliasChoices("playlist_title", "title"),
        ),
    ] = ""
    uploader: str | None = None
    thumbnails: list[Thumbnail] = []

    @property
    def _resolve_class(self):
        return Playlist


class Playlist(LazyPlaylist):
    type: Annotated[Literal["playlist"], TypeField] = "playlist"  # type: ignore
    entries: EntriesField  # type: ignore


class Search(MediaList):
    type: Literal["search"] = "search"
    extractor: ExtractorField

    query: str = ""
    service: str = ""

    entries: EntriesField  # type: ignore


Entries: TypeAlias = list[LazyMedia | LazyPlaylist]
EntriesField = Annotated[Entries, Field(alias="entries", min_length=1)]
