from __future__ import annotations

from abc import ABC
from typing import Annotated, Literal

from pydantic import AliasChoices, AnyUrl, Discriminator, Field, Tag
from typing_extensions import TypeVar

from remora.models._base import BaseList
from remora.models.media._base import (
    URL_CHOICES,
    BaseExtract,
    ExtractID,
    is_ydl_media,
)
from remora.models.media.item import LazyMedia

__all__ = [
    "EntriesList",
    "LazyPlaylist",
    "Playlist",
    "SearchList",
]

# Discriminator
_PLAYLIST_EXTRACTOR_KEYS = ("YoutubeTab",)


def _infer_extract_type(data) -> str:
    if is_ydl_media(data):
        extractor_key = data.get("extractor_key") or data.get("ie_key")

        if (
            data.get("_type") == "playlist"
            or (extractor_key in _PLAYLIST_EXTRACTOR_KEYS)
            or data.get("entries")
        ):
            return "playlist"

        return "media"
    elif isinstance(data, (LazyMedia, LazyPlaylist)):
        return data.type
    raise ValueError("Unable to determine media type")


_TMedia = TypeVar("_TMedia", bound=LazyMedia)
_TPlaylist = TypeVar("_TPlaylist", bound="LazyPlaylist")
_ExtractDiscriminator = Annotated[
    Annotated[_TMedia, Tag("media")] | Annotated[_TPlaylist, Tag("playlist")],
    Discriminator(_infer_extract_type),
]

_ExtractType = _ExtractDiscriminator[LazyMedia, "LazyPlaylist"]
_Entry = TypeVar("_Entry", bound=_ExtractType, default=_ExtractType)


# Entries List
class EntriesList(BaseList[_Entry]):
    def medias(self) -> EntriesList[LazyMedia]:
        return EntriesList(item for item in self.root if isinstance(item, LazyMedia))

    def playlists(self) -> EntriesList[LazyPlaylist]:
        return EntriesList(item for item in self.root if isinstance(item, LazyPlaylist))


class _BaseList(ABC, BaseExtract):
    entries: Annotated[EntriesList, Field(repr=False, default_factory=EntriesList)]


# Search
class SearchList(_BaseList):
    type: Literal["search"] = "search"
    service: str
    query: str


# Playlist
class LazyPlaylist(_BaseList, ExtractID):
    type: Literal["playlist"] = "playlist"

    id: Annotated[str, Field(alias="playlist_id")]
    url: Annotated[
        AnyUrl,
        Field(validation_alias=AliasChoices("playlist_url", *URL_CHOICES)),
    ]
    title: Annotated[str, Field(alias="playlist_title")] = ""


class Playlist(LazyPlaylist): ...
