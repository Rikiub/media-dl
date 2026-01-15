from abc import ABC, abstractmethod
from typing import Annotated, Generic, TypeVar

from pydantic import AliasChoices, Field
from typing_extensions import Self

from media_dl.models.base import YDLSerializable

# Types
PLAYLIST_EXTRACTORS = ["YoutubeTab"]
URL_CHOICES = ["original_url", "url", "webpage_url"]

# Fields
TypeField = Field(alias="_type")
ExtractorField = Annotated[
    str,
    Field(
        alias="extractor_key",
        validation_alias=AliasChoices("extractor_key", "ie_key"),
    ),
]


# Items
class Extract(YDLSerializable):
    """Base identifier for media objects."""

    extractor: ExtractorField
    url: Annotated[str, Field(validation_alias=AliasChoices(*URL_CHOICES))]
    id: str

    @classmethod
    def from_url(
        cls,
        url: str,
        use_cache: bool = True,
    ) -> Self:
        from media_dl.extractor import extract_url

        return extract_url(url, use_cache)  # type: ignore


T = TypeVar("T", bound=Extract)


class LazyExtract(ABC, Extract, Generic[T]):
    def resolve(self, use_cache: bool = True) -> T:
        """Get the full model.

        Returns:
            Updated version of the model.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        return self._resolve_class.from_url(self.url, use_cache)

    @property
    @abstractmethod
    def _resolve_class(self) -> type[T]: ...
