from abc import ABC, abstractmethod
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, Field, computed_field
from typing_extensions import Self

from media_dl.cache import load_info, save_info
from media_dl.extractor import extract_url, is_playlist, is_stream
from media_dl.ydl.types import YDLExtractInfo

UrlAlias = AliasChoices("original_url", "url")
ExtractorKey = Annotated[
    str,
    Field(
        alias="extractor_key",
        validation_alias=AliasChoices("extractor_key", "ie_key"),
    ),
]
TypeField = Annotated[Literal["url", "playlist"], Field(alias="_type")]


class ExtractID(ABC, BaseModel):
    """Base identifier for media objects."""

    type: TypeField = "url"
    extractor: ExtractorKey
    url: Annotated[str, Field(validation_alias=UrlAlias)]
    id: str

    @classmethod
    def from_url(cls, url: str) -> Self:
        # Load from cache
        if info := load_info(url):
            return cls.model_validate_json(info)

        # Fetch info
        info = extract_url(url)
        isPlaylist = is_playlist(info)

        try:
            cls = cls(type="playlist" if isPlaylist else "url", **info)
        except ValueError:
            raise TypeError(
                f"{url} fetching was successful but data doesn't match with '{cls.__name__}' model. Please use '{'Playlist' if isPlaylist else 'Stream'}' instead."
            )

        # Save to cache
        save_info(cls.url, cls.model_dump_json())
        return cls

    def as_info_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True)


class BaseDataList(ABC, BaseModel):
    type: TypeField = "playlist"
    entries: Annotated[list, Field(alias="entries")]

    @computed_field
    @property
    @abstractmethod
    def streams(self) -> list:
        results = []
        for entry in self.entries:
            if is_stream(entry):
                results.append(entry)
        return results

    @computed_field
    @property
    @abstractmethod
    def playlists(self) -> list:
        results = []
        for entry in self.entries:
            if is_playlist(entry):
                results.append(entry)
        return results

    def as_info_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True)
