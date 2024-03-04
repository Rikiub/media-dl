from dataclasses import dataclass

from media_dl.extractor import InfoExtractor, InfoDict
from media_dl.cache import GLOBAL_INFO


@dataclass(slots=True, frozen=True)
class MetaID:
    """Base identifier for all media objects."""

    extractor: str
    id: str
    url: str

    def get_info(self) -> InfoDict:
        return GLOBAL_INFO.load(self.extractor, self.id) or extract_url(self.url)


def extract_url(url: str) -> InfoDict:
    return InfoExtractor().extract_url(url)


def extract_thumbnail(info: InfoDict) -> str:
    if t := info.get("thumbnail"):
        return t
    elif t := info.get("thumbnails"):
        return t[-1]["url"]
    else:
        return ""


def extract_meta(info: InfoDict) -> tuple[str, str, str]:
    """Helper for extract essential information from info dict.

    Returns:
        Tuple with 'extractor', 'id', 'url'.
    """

    try:
        extractor = info.get("extractor_key") or info["ie_key"]
        id = info["id"]
        url = info.get("original_url") or info["url"]
    except KeyError:
        raise TypeError("Must have the required keys: 'extractor_key', 'id', 'url'.")

    return extractor, id, url
