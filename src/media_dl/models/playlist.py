from __future__ import annotations

from typing import Annotated

from pydantic import AliasChoices, Field, OnErrorOmit

from media_dl.models.base import URL_CHOICES, BaseDataList, ExtractID
from media_dl.models.metadata import Thumbnail
from media_dl.models.stream import LazyStreams


class LazyPlaylist(BaseDataList, ExtractID):
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

    streams: LazyStreams = []
    playlists: LazyPlaylists = []

    def fetch(self) -> Playlist:
        """Fetch real playlist.

        Returns:
            Updated version of self Playlist.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        return Playlist.from_url(self.url)


LazyPlaylists = Annotated[
    list[OnErrorOmit[LazyPlaylist]],
    Field(
        alias="playlists",
        validation_alias=AliasChoices("playlists", "entries"),
    ),
]


class Playlist(LazyPlaylist): ...
