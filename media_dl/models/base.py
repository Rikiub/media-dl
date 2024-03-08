from abc import ABC, abstractmethod
from dataclasses import dataclass

from media_dl.extractor import InfoExtractor, InfoDict
from media_dl.cache import GLOBAL_INFO


_EXTR = InfoExtractor()


@dataclass(slots=True, frozen=True)
class ExtractID(ABC):
    """Base identifier for all media objects.

    Essential to downloaders.
    """

    extractor: str
    id: str
    url: str

    def __eq__(self, value) -> bool:
        return self.id == value.id

    def get_info_dict(self) -> InfoDict:
        """Get the original `yt-dlp` info-dict of the object. Has more information but isn't safe.

        It is more for advanced users. You can check it if you know what you're doing.
        """

        return GLOBAL_INFO.load(self.extractor, self.id) or _EXTR.extract_url(self.url)

    @classmethod
    def from_url(cls, url: str):
        info = _EXTR.extract_url(url)
        return cls._from_info(info)

    @classmethod
    @abstractmethod
    def _from_info(cls, info: InfoDict):
        raise NotImplementedError()
