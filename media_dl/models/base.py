from abc import ABC, abstractmethod
from dataclasses import dataclass

from media_dl import extractor
from media_dl.helper import InfoDict


@dataclass(slots=True, frozen=True)
class ExtractID(ABC):
    """Base identifier for media objects."""

    extractor: str
    id: str
    url: str

    @classmethod
    def from_url(cls, url: str):
        info = extractor.from_url(url)
        return cls._from_info(info)

    @classmethod
    @abstractmethod
    def _from_info(cls, info: InfoDict):
        raise NotImplementedError()

    def __eq__(self, value) -> bool:
        return self.id == value.id
