from media_dl.extractor import serializer, raw
from media_dl.extractor.raw import SEARCH_PROVIDER
from media_dl.models import Stream, Playlist


def extract_url(url: str) -> Stream | Playlist:
    """Extract and serialize information from URL.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.from_url(url)
    data = serializer.info_to_dataclass(info)
    return data


def extract_search(query: str, provider: SEARCH_PROVIDER) -> list[Stream]:
    """Extract and serialize information from search provider.

    Returns:
        List of streams founded in the search (Streams will be incomplete).

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.from_search(query, provider)
    data = serializer.info_to_dataclass(info)

    if isinstance(data, Playlist):
        return data.streams
    else:
        raise TypeError("Search not return a Playlist.")
