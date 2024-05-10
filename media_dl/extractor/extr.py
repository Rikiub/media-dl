from media_dl.exceptions import ExtractError

from media_dl.extractor import raw, serializer
from media_dl.extractor.raw import SEARCH_PROVIDER
from media_dl.models import Playlist, LazyStreams, Stream


def extract_search(query: str, provider: SEARCH_PROVIDER) -> LazyStreams:
    """Extract information from search provider.

    Returns:
        Lazy list of streams.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.extract_search(query, provider)
    return LazyStreams._from_info(info)


def extract_url(url: str) -> Stream | Playlist:
    """Extract information from URL.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.extract_url(url)

    if serializer.is_stream(info):
        return Stream._from_info(info)
    elif serializer.is_playlist(info):
        return Playlist._from_info(info)
    else:
        raise ExtractError("Extract return a invalid result.")
