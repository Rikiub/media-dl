from typing import Annotated, Literal, TypeVar

from pydantic import AliasChoices, BaseModel, Field, field_validator
from typing_extensions import Self

from media_dl.cache import load_info, save_info
from media_dl.extractor import extract_search, extract_url, is_playlist, is_stream
from media_dl.types import SEARCH_PROVIDER
from media_dl.ydl.types import YDLExtractInfo

# Types
URL_CHOICES = ["original_url", "url"]
ExtractorField = Annotated[
    str,
    Field(
        alias="extractor_key",
        validation_alias=AliasChoices("extractor_key", "ie_key"),
    ),
]
TypeField = Annotated[
    Literal["url", "playlist"],
    Field(alias="_type"),
]


# Interfaces
class Serializable(BaseModel):
    def to_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True)

    def to_ydl_json(self) -> str:
        return self.model_dump_json(by_alias=True)

    @classmethod
    def from_ydl_json(cls, data: str) -> Self:
        return cls.model_validate_json(data, by_alias=True)


# Helpers
T = TypeVar("T", bound=Serializable)


def _load_cache(cls: type[T], url: str):
    if info := load_info(url):
        try:
            return cls.from_ydl_json(info)
        except ValueError:
            raise TypeError(
                f"'{url}' fetched from cache but data doesn't match with model"
            )


# Identifier
class Extract(Serializable):
    """Base identifier for media objects."""

    type: TypeField = "url"
    extractor: ExtractorField
    url: Annotated[str, Field(validation_alias=AliasChoices(*URL_CHOICES))]
    id: str

    @classmethod
    def from_url(
        cls,
        url: str,
        use_cache: bool = True,
    ) -> Self:
        # Load from cache
        if info := use_cache and _load_cache(cls, url):
            return info

        # Fetch info
        info = extract_url(url)
        isPlaylist = is_playlist(info)

        try:
            cls = cls(type="playlist" if isPlaylist else "url", **info)
        except ValueError:
            raise TypeError(
                f"'{url}' fetching was successful but data doesn't match with '{cls.__name__}' model. Please use '{'Playlist' if isPlaylist else 'Stream'}' instead."
            )

        # Save to cache
        if use_cache:
            save_info(cls.url, cls.to_ydl_json())

        return cls


# Lists
class ExtractList(Serializable):
    type: TypeField = "playlist"
    streams: list
    playlists: list

    @field_validator("streams", mode="before")
    def _validate_streams(cls, data):
        if isinstance(data, list):
            return [item for item in data if is_stream(item)]

    @field_validator("playlists", mode="before")
    def _validate_playlists(cls, data):
        if isinstance(data, list):
            return [item for item in data if is_playlist(item)]


class ExtractSearch(ExtractList):
    extractor: ExtractorField

    query: str = ""
    provider: str = ""

    @classmethod
    def from_query(
        cls,
        query: str,
        provider: SEARCH_PROVIDER,
        limit: int = 20,
        use_cache: bool = True,
    ) -> Self:
        # Load from cache
        if info := use_cache and _load_cache(cls, query):
            return info

        # Fetch info
        info = extract_search(query, provider, limit)
        cls = cls(query=query, provider=provider, **info)

        # Save to cache
        if use_cache:
            save_info(cls.query, cls.to_ydl_json())

        return cls
