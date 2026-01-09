from abc import ABC
from typing import Annotated, Literal, TypeAlias

from pydantic import AliasChoices, BaseModel, Field, field_validator
from typing_extensions import Self

from media_dl.cache import load_info, save_info
from media_dl.extractor import extract_url, is_playlist, is_stream
from media_dl.ydl.types import YDLExtractInfo

URL_CHOICES = ("original_url", "url")
ExtractorKey = Annotated[
    str,
    Field(
        alias="extractor_key",
        validation_alias=AliasChoices("extractor_key", "ie_key"),
    ),
]
TypeField: TypeAlias = Annotated[Literal["url", "playlist"], Field(alias="_type")]


class BaseData(ABC, BaseModel):
    def as_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True)

    def as_ydl_json(self) -> str:
        return self.model_dump_json(by_alias=True)


class ExtractID(BaseData):
    """Base identifier for media objects."""

    type: TypeField = "url"
    extractor: ExtractorKey
    url: Annotated[str, Field(validation_alias=AliasChoices(*URL_CHOICES))]
    id: str

    @classmethod
    def from_url(cls, url: str) -> Self:
        # Load from cache
        if info := load_info(url):
            try:
                return cls.model_validate_json(info)
            except ValueError:
                raise TypeError(
                    f"'{url}' fetched from cache but data doesn't match with model"
                )

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
        save_info(cls.url, cls.as_ydl_json())
        return cls


class BaseDataList(BaseData):
    type: TypeField = "playlist"
    streams: list
    playlists: list

    @field_validator("streams", mode="before")
    def _streams(cls, value: list):
        results = []
        for entry in value:
            if is_stream(entry):
                results.append(entry)
        return results

    @field_validator("playlists", mode="before")
    def _playlists(cls, value: list):
        results = []
        for entry in value:
            if is_playlist(entry):
                results.append(entry)
        return results
