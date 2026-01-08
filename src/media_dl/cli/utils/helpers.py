from loguru import logger

from media_dl.cli.utils.completions import SEARCH_TARGET
from media_dl.exceptions import ExtractError
from media_dl.models.playlist import Playlist, SearchQuery
from media_dl.models.stream import Stream
from media_dl.rich import Status


def extract_query(
    target: SEARCH_TARGET, entry: str, quiet: bool = False
) -> Stream | Playlist | SearchQuery:
    with Status("Please wait", disable=quiet):
        if target == "url":
            try:
                logger.info('🔎 Extract URL: "{url}".', url=entry)
                result = Stream.from_url(entry)
            except TypeError:
                try:
                    result = Playlist.from_url(entry)
                    logger.info('🔎 Playlist title: "{title}".', title=result.title)
                except TypeError:
                    raise ExtractError(f'Unable to fetch data from "{entry}"')
        else:
            logger.info(
                '🔎 Search from {extractor}: "{query}".',
                extractor=target,
                query=entry,
            )
            result = SearchQuery(entry, target)
    return result
