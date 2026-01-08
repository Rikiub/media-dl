from __future__ import annotations

from typing import Annotated

from pydantic import Field, OnErrorOmit, computed_field

from media_dl.models.base import BaseDataList, ExtractID, UrlAlias
from media_dl.models.metadata import Thumbnail
from media_dl.models.stream import LazyStream, LazyStreams


class LazyPlaylist(BaseDataList, ExtractID):
    url: Annotated[str, Field(alias="playlist_url", validation_alias=UrlAlias)]
    id: Annotated[str, Field(alias="playlist_id", validation_alias="id")]

    title: Annotated[str, Field(alias="playlist_title", validation_alias="title")] = ""
    uploader: str | None = None
    thumbnails: list[Thumbnail] = []

    @computed_field
    @property
    def streams(self) -> LazyStreams:
        return [LazyStream(**info) for info in self.entries]

    @computed_field
    @property
    def playlists(self) -> LazyPlaylists:
        return [LazyPlaylist(**info) for info in self.entries]

    def fetch(self) -> Playlist:
        """Fetch real playlist.

        Returns:
            Updated version of self Playlist.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        return Playlist.from_url(self.url)


LazyPlaylists = list[OnErrorOmit[LazyPlaylist]]


class Playlist(LazyPlaylist): ...
