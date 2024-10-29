from media_dl.exceptions import ExtractError
from media_dl.extractor import raw
from media_dl.extractor.raw import SEARCH_PROVIDER
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStreams, Stream, DeferredStream


def extract_search(query: str, provider: SEARCH_PROVIDER) -> LazyStreams:
    """Extract information from search provider.

    Returns:
        Lazy list of streams.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.extract_search(query, provider)
    return LazyStreams([DeferredStream(**i) for i in info["entries"]])


def extract_url(url: str) -> Stream | Playlist:
    """Extract information from URL.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.extract_url(url)

    try:
        try:
            return Playlist(**info)
        except ValueError:
            return Stream(**info)
    except ValueError:
        raise ExtractError("Extract return a invalid result.")
