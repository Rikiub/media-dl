import logging
from media_dl.exceptions import ExtractError
from media_dl.extractor.cache import JsonCache
from media_dl.extractor import info as info_extractor
from media_dl.extractor.helper import is_playlist, is_stream
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStream, Stream
from media_dl.types import SEARCH_PROVIDER


log = logging.getLogger(__name__)


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
        raise _exception(query)


def extract_url(url: str) -> Stream | Playlist:
    """Extract information from URL.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        ExtractError: Error happen when extract.
    """

    # Try: get cache
    if info := JsonCache(url).get():
        log.debug("Using cache of: %s", url)

        try:
            return Stream.model_validate_json(info)
        except ValueError:
            JsonCache(url).remove()
            log.info("Cache is corrupted, deleting and trying again.")

    info = info_extractor.extract_url(url)

    try:
        if is_stream(info):
            stream = Stream(**info)

            JsonCache(url).save(stream.model_dump_json(by_alias=True))
            stream.has_cache = True

            log.debug("Save cache of: %s", url)
        elif is_playlist(info):
            stream = Playlist(**info)
        else:
            raise ValueError()

        return stream
    except ValueError:
        raise _exception(url)


def _exception(url: str):
    return ExtractError(
        f'"{url}" did not return valid data or lacks downloadable formats.'
    )
