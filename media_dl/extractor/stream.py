from media_dl.exceptions import ExtractError
from media_dl.extractor import info as info_extractor
from media_dl.extractor.helper import is_playlist, is_stream
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStream, Stream
from media_dl.types import SEARCH_PROVIDER


def extract_search(query: str, provider: SEARCH_PROVIDER) -> list[LazyStream]:
    """Extract information from search provider.

    Returns:
        Lazy list of streams.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = info_extractor.extract_search(query, provider)

    if is_playlist(info):
        return [LazyStream(**i) for i in info["entries"]]
    else:
        raise _extractor_exception(query)


def extract_url(url: str) -> Stream | Playlist:
    """Extract information from URL.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = info_extractor.extract_url(url)

    try:
        if is_stream(info):
            return Stream(**info)
        elif is_playlist(info):
            return Playlist(**info)
        else:
            raise ValueError()
    except ValueError:
        raise _extractor_exception(url)


def _extractor_exception(url: str):
    return ExtractError(
        f'"{url}" did not return valid data or lacks downloadable formats.'
    )
