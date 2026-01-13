from __future__ import annotations

from typing import Annotated
from typing_extensions import Self

from pydantic import AliasChoices, Field, model_validator

from media_dl.models.content.base import (
    URL_CHOICES,
    ExtractList,
    ExtractSearch,
    LazyExtract,
)
from media_dl.models.content.media import LazyMedia
from media_dl.models.content.metadata import Thumbnail


class MediaList(ExtractList):
    medias: LazyMedias = []
    playlists: LazyPlaylists = []

    @model_validator(mode="after")
    def _validate_lists(self) -> Self:
        if not self.medias and not self.playlists:
            raise ValueError("Must contain at least one Media or Playlist.")
        return self


class LazyPlaylist(MediaList, LazyExtract["Playlist"]):
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
    def _target_class(self):
        return Playlist


class Playlist(LazyPlaylist): ...


class Search(MediaList, ExtractSearch): ...


LazyMedias = Annotated[
    list[LazyMedia],
    Field(
        alias="medias",
        validation_alias=AliasChoices("medias", "entries"),
    ),
]
LazyPlaylists = Annotated[
    list[LazyPlaylist],
    Field(
        alias="playlists",
        validation_alias=AliasChoices("playlists", "entries"),
    ),
]
