from abc import ABC
from typing import Annotated

from pydantic import AliasChoices, BaseModel, Field
from typing_extensions import Self

from media_dl.extractor import is_playlist, extract_url

URL_TYPE = ("original_url", "url")


class ExtractID(ABC, BaseModel):
    """Base identifier for media objects."""

    extractor: Annotated[
        str,
        Field(
            alias="extractor_key",
            validation_alias=AliasChoices("extractor_key", "ie_key"),
        ),
    ]
    url: Annotated[str, Field(validation_alias=AliasChoices(*URL_TYPE))]
    id: str

    @classmethod
    def from_url(cls, url: str) -> Self:
        info = extract_url(url)

        try:
            return cls(**info)
        except ValueError:
            raise TypeError(
                f"{url} fetching was successful but data doesn't match with {cls.__name__} model. Please use {'Stream' if is_playlist(info) else 'Playlist'} instead."
            )
