from loguru import logger
from typing import Annotated
from typer import Option, Typer, Argument

from media_dl.exceptions import ExtractError
from media_dl.rich import Status, CONSOLE
from media_dl.cli.utils.options import QuietOption
from media_dl.cli.utils.completions import complete_query, parse_queries

app = Typer()


def print_to_console(data, json: bool):
    if json:
        print(data.model_dump_json())
    else:
        CONSOLE.print(data)


@app.command(no_args_is_help=True)
def extract(
    query: Annotated[
        str,
        Argument(
            help="""[green]URL[/] or [green]query[/] to process.
            \n
            - Insert a [green]URL[/] to extract [grey62](Default)[/].\n
            - Select a [green]PROVIDER[/] to search and extract.
            """,
            show_default=False,
            autocompletion=complete_query,
            metavar="URL | PROVIDER",
        ),
    ],
    json: Annotated[
        bool,
        Option(
            "--json",
            help="Output as JSON",
        ),
    ] = False,
    quiet: QuietOption = False,
):
    # Lazy Import
    with Status("Starting...", disable=quiet):
        from media_dl.cli.utils.helpers import extract_query
        from media_dl.models.playlist import SearchQuery

    for target, entry in parse_queries([query]):
        try:
            result = extract_query(target, entry, quiet)

            if isinstance(result, SearchQuery):
                for index, entry in enumerate(result.streams, 1):
                    with Status(
                        f"Fetching {entry.__class__.__name__} {index}...", disable=quiet
                    ):
                        entry = entry.fetch()
                    print_to_console(entry, json)
            else:
                print_to_console(result, json)
        except ExtractError as error:
            logger.error("❌ {error}", error=str(error))
