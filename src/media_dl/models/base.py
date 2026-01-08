from abc import ABC
from typing import Annotated

from pydantic import AliasChoices, BaseModel, Field, field_validator
from typing_extensions import Self

from media_dl.extractor import extract_url, is_playlist, is_stream
from media_dl.ydl.types import InfoDict

UrlAlias = AliasChoices("original_url", "url")
ExtractorKey = Annotated[
    str,
    Field(
        alias="extractor_key",
        validation_alias=AliasChoices("extractor_key", "ie_key"),
    ),
]
EntriesField = Field(validation_alias="entries")


class ExtractID(ABC, BaseModel):
    """Base identifier for media objects."""

    extractor: ExtractorKey
    url: Annotated[str, Field(validation_alias=UrlAlias)]
    id: str

    @classmethod
    def from_url(cls, url: str) -> Self:
        info = extract_url(url)

        try:
            return cls(**info)
        except ValueError:
            raise TypeError(
                f"{url} fetching was successful but data doesn't match with '{cls.__name__}' model. Please use '{'Playlist' if is_playlist(info) else 'Stream'}' instead."
            )

    def as_info_dict(self) -> InfoDict:
        return self.model_dump(by_alias=True)


class BaseDataList(BaseModel):
    streams: Annotated[list, EntriesField]
    playlists: Annotated[list, EntriesField]

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
