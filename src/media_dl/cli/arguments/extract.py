from loguru import logger
from typing import Annotated
from typer import Typer, Argument

from media_dl.rich import Status, CONSOLE
from media_dl.cli.utils.options import QuietOption
from media_dl.cli.utils.completions import complete_query, parse_queries

app = Typer()


@app.command(no_args_is_help=True)
def extract(
    query: Annotated[
        str,
        Argument(
            help="""[green]URLs[/] and [green]queries[/] to process.
            \n
            - Insert a [green]URL[/] to download [grey62](Default)[/].\n
            - Select a [green]PROVIDER[/] to search and download.
            """,
            show_default=False,
            autocompletion=complete_query,
            metavar="URL | PROVIDER",
        ),
    ],
    quiet: QuietOption = False,
):
    # Lazy Import
    with Status("Starting...", disable=quiet):
        from media_dl.models.playlist import Playlist, SearchQuery
        from media_dl.models.stream import Stream

    for target, entry in parse_queries([query]):
        with Status("Fetching...", disable=quiet):
            if target == "url":
                try:
                    result = Stream.from_url(entry)
                    logger.info('🔎 Extract URL: "{url}".', url=entry)
                except TypeError:
                    result = Playlist.from_url(entry)
                    logger.info('🔎 Playlist title: "{title}".', title=result.title)
            else:
                logger.info(
                    '🔎 Search from {extractor}: "{query}".',
                    extractor=target,
                    query=entry,
                )
                result = SearchQuery(entry, target)

    CONSOLE.print(result)
