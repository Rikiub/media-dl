from __future__ import annotations

from abc import ABC
from typing import Annotated

from pydantic import AliasChoices, Field

from media_dl.models.content.base import (
    URL_CHOICES,
    ExtractList,
    ExtractSearch,
    LazyType,
)
from media_dl.models.content.media import LazyMedia
from media_dl.models.content.metadata import Thumbnail


class BaseList(ABC, ExtractList):
    medias: LazyMedias = []
    playlists: LazyPlaylists = []


class LazyPlaylist(BaseList, LazyType["Playlist"]):
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


class Search(BaseList, ExtractSearch): ...


LazyPlaylists = Annotated[
    list[LazyPlaylist],
    Field(
        alias="playlists",
        validation_alias=AliasChoices("playlists", "entries"),
    ),
]
LazyMedias = Annotated[
    list[LazyMedia],
    Field(
        alias="medias",
        validation_alias=AliasChoices("medias", "entries"),
    ),
]
