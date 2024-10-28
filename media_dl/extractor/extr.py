from media_dl.exceptions import ExtractError
from media_dl.extractor import raw, serializer
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

    if serializer.is_stream(info):
        return Stream(**info)
    elif serializer.is_playlist(info):
        return Playlist(**info)
    else:
        raise ExtractError("Extract return a invalid result.")
