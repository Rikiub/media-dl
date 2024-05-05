from media_dl.exceptions import ExtractError

from media_dl.extractor import raw, serializer
from media_dl.extractor.raw import SEARCH_PROVIDER
from media_dl.models import Playlist, LazyStreams, Stream


def extract_url(url: str) -> Stream | Playlist:
    """Extract and serialize information from URL.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.extract_url(url)

    try:
        if serializer.is_stream(info):
            return Stream._from_info(info)
        elif serializer.is_playlist(info):
            return Playlist._from_info(info)
        else:
            raise TypeError()
    except TypeError:
        raise ExtractError(info, "not is a valid info dict.")


def extract_search(query: str, provider: SEARCH_PROVIDER) -> LazyStreams:
    """Extract and serialize information from search provider.

    Returns:
        List of streams founded in the search (Streams will be incomplete).

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.extract_search(query, provider)

    try:
        return LazyStreams._from_info(info)
    except TypeError:
        raise ExtractError("Search returns a invalid result.")
