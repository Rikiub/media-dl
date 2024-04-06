from abc import ABC, abstractmethod
from dataclasses import dataclass

from media_dl.extractor import InfoExtractor, InfoDict


_EXTR = InfoExtractor()


@dataclass(slots=True, frozen=True)
class ExtractID(ABC):
    """Base identifier for all media objects.

    Essential to downloaders.
    """

    extractor: str
    id: str
    url: str

    @classmethod
    def from_url(cls, url: str):
        info = _EXTR.extract_url(url)
        return cls._from_info(info)

    @classmethod
    @abstractmethod
    def _from_info(cls, info: InfoDict):
        raise NotImplementedError()

    def __eq__(self, value) -> bool:
        return self.id == value.id
