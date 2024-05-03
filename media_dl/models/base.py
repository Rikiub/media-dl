from abc import ABC, abstractmethod
from dataclasses import dataclass

from media_dl.extractor import raw
from media_dl._ydl import InfoDict


@dataclass(slots=True, frozen=True, order=True)
class ExtractID(ABC):
    """Base identifier for media objects."""

    extractor: str
    id: str
    url: str

    @classmethod
    def from_url(cls, url: str):
        info = raw.from_url(url)
        return cls._from_info(info)

    @classmethod
    @abstractmethod
    def _from_info(cls, info: InfoDict):
        raise NotImplementedError()
