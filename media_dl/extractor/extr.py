from media_dl.extractor import raw, info_helper
from media_dl.extractor.raw import SEARCH_PROVIDER, InfoDict
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
    data = _info_to_dataclass(info)
    return data


def extract_search(query: str, provider: SEARCH_PROVIDER) -> list[Stream]:
    """Extract and serialize information from search provider.

    Returns:
        List of streams founded in the search (Streams will be incomplete).

    Raises:
        ExtractError: Error happen when extract.
    """

    info = raw.from_search(query, provider)
    data = _info_to_dataclass(info)

    if isinstance(data, Playlist):
        return data.streams
    else:
        raise TypeError("Search not return a Playlist.")


def _info_to_dataclass(info: InfoDict) -> Stream | Playlist:
    """Serialize information from a info dict.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        TypeError: Not is a valid info dict.
    """

    if info_helper.is_playlist(info):
        return Playlist._from_info(info)
    elif info_helper.is_stream(info):
        return Stream._from_info(info)
    else:
        raise TypeError(info, "not is a valid info dict.")
