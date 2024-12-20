from abc import ABC
from typing import Annotated
from typing_extensions import Self

from pydantic import AliasChoices, BaseModel, Field

from media_dl.extractor.helper import is_playlist
from media_dl.extractor.info import extract_url


class ExtractID(BaseModel, ABC):
    """Base identifier for media objects."""

    extractor: Annotated[
        str,
        Field(
            alias="extractor_key",
            validation_alias=AliasChoices("extractor_key", "ie_key"),
        ),
    ]
    url: Annotated[str, Field(validation_alias=AliasChoices("original_url", "url"))]
    id: str

    @classmethod
    def from_url(cls, url: str) -> Self:
        info = extract_url(url)

        try:
            return cls(**info)
        except ValueError:
            raise TypeError(
                f"{url} fetching was successful but data doesn't match with {cls.__name__} model. Please use {'Playlist' if is_playlist(info) else 'Stream'} instead."
            )
