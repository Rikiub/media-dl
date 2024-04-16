"""
Info extractor and serializer of queries.

To use, should be imported as module.
>>> from media_dl import extractor

And then, you can perform various actions:

For URLs:
>>> url = "https://www.youtube.com/watch?v=BaW_jenozKc"
>>> extractor.extract_url(url)

For searching:
>>> extractor.extract_search("Sub Urban - Cradles", provider="ytmusic")

For helpers:
>>> extractor.serializer.info_is_playlist(info)
"""

from media_dl.extractor.raw import SEARCH_PROVIDER
from media_dl.extractor import serializer, raw
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
