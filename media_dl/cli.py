try:
    from typer import Argument, BadParameter, Option, Typer
except ImportError:
    raise ImportError("Typer is required to use CLI features.")

import logging
from pathlib import Path
from typing import Annotated, Generator, Literal, get_args

from strenum import StrEnum

from media_dl.logging import init_logging
from media_dl.rich import Status
from media_dl.types import APPNAME, FILE_FORMAT, SEARCH_PROVIDER, VIDEO_RES

log = logging.getLogger(__name__)
app = Typer(rich_markup_mode="rich")


# Typer: types
Format = StrEnum("Format", get_args(FILE_FORMAT))
SearchFrom = StrEnum("SearchFrom", get_args(Literal["url", SEARCH_PROVIDER]))


# Typer: helpers
class HelpPanel(StrEnum):
    file = "File"
    downloader = "Downloader"
    other = "Other"


def show_version(show: bool) -> None:
    if show:
        from importlib.metadata import version

        print(version(Path(__file__).parent.name))

        raise SystemExit()


# Typer: completions
def complete_query(incomplete: str) -> Generator[str, None, None]:
    for name in SearchFrom:
        if name.value.startswith(incomplete):
            yield name.value + ":"


def complete_resolution() -> Generator[str, None, None]:
    for name in get_args(VIDEO_RES):
        yield str(name)


def complete_output(incomplete: str) -> Generator[str, None, None]:
    if incomplete.endswith("{"):
        from media_dl.template.keys import OUTPUT_TEMPLATES

        for key in OUTPUT_TEMPLATES:
            yield incomplete + key + "}"


def parse_queries(queries: list[str]) -> Generator[tuple[SearchFrom, str], None, None]:
    providers = [entry.name for entry in SearchFrom]

    for entry in queries:
        selection = entry.split(":")[0]

        if entry.startswith(("http://", "https://")):
            target = SearchFrom["url"]
        elif selection in providers:
            target = SearchFrom[selection]
            entry = entry.split(":")[1]
        else:
            completed = [i for i in complete_query(selection)]

            if completed:
                msg = f"Did you mean '{completed[0]}'?"
            else:
                msg = "Should be URL or search PROVIDER."

            raise BadParameter(f"'{selection}' is invalid. {msg}")

        yield target, entry


# Typer: app
@app.command(no_args_is_help=True)
def download(
    query: Annotated[
        list[str],
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
    format: Annotated[
        Format,
        Option(
            "--format",
            "-f",
            help="""File type to request.\n
            - To get BEST, select [green]video[/] or [green]audio[/] [grey62](Fast)[/].\n
            - To convert, select a file [green]EXTENSION[/] [grey62](Slow)[/].
            """,
            metavar="TYPE | EXTENSION",
            prompt="""
What format you want request?

- To get BEST, select 'video' or 'audio' (Fast).
- To convert, select a file EXTENSION (Slow).

""",
            prompt_required=False,
            show_default=False,
            rich_help_panel=HelpPanel.file,
        ),
    ] = Format["video"],
    quality: Annotated[
        int | None,
        Option(
            "--quality",
            "-q",
            help="Prefered video/audio quality to filter.",
            rich_help_panel=HelpPanel.file,
            autocompletion=complete_resolution,
            show_default=False,
        ),
    ] = None,
    output: Annotated[
        Path,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            rich_help_panel=HelpPanel.file,
            autocompletion=complete_output,
            show_default=False,
            dir_okay=True,
            file_okay=False,
        ),
    ] = Path.cwd(),
    ffmpeg: Annotated[
        Path | None,
        Option(
            "--ffmpeg",
            help="FFmpeg executable to use.",
            rich_help_panel=HelpPanel.downloader,
            show_default=False,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    threads: Annotated[
        int,
        Option(
            "--threads",
            help="Limit of simultaneous downloads.",
            rich_help_panel=HelpPanel.downloader,
        ),
    ] = 5,
    quiet: Annotated[
        bool,
        Option(
            "--quiet",
            help="Supress screen information.",
            rich_help_panel=HelpPanel.other,
        ),
    ] = False,
    verbose: Annotated[
        bool,
        Option(
            "--verbose",
            help="Display more information on screen.",
            rich_help_panel=HelpPanel.other,
        ),
    ] = False,
    version: Annotated[
        bool,
        Option(
            "--version",
            help="Show current version and exit.",
            rich_help_panel=HelpPanel.other,
            callback=show_version,
        ),
    ] = False,
):
    """Download any video/audio you want from a simple URL ✨"""

    if quiet:
        log_level = logging.CRITICAL
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    init_logging(log_level)

    # Lazy Import
    with Status("Starting...", disable=quiet):
        from media_dl.downloader.stream import StreamDownloader
        from media_dl.exceptions import DownloadError, ExtractError
        from media_dl.models.playlist import Playlist, SearchQuery
        from media_dl.models.stream import Stream

    # Initialize Downloader
    try:
        downloader = StreamDownloader(
            format=format.value,
            quality=quality,
            output=output,
            ffmpeg=ffmpeg,
            threads=threads,
            show_progress=not quiet,
        )
    except FileNotFoundError as err:
        raise BadParameter(str(err))

    if downloader.config.convert and not downloader.config.ffmpeg:
        log.warning(
            "❗ FFmpeg not installed. File conversion and metadata embeding will be disabled."
        )

    for target, entry in parse_queries(query):
        try:
            with Status("Please wait", disable=quiet):
                if target.value == "url":
                    log.info('🔎 Extract URL: "%s".', entry)

                    try:
                        result = Stream.from_url(entry)
                    except TypeError:
                        result = Playlist.from_url(entry)
                        log.info('🔎 Playlist title: "%s".', result.title)
                else:
                    log.info('🔎 Search from %s: "%s".', target.value, entry)
                    result = SearchQuery(entry, target.value).streams[0]

            downloader.download_all(result)
            log.info("✅ Download Finished.")
        except (ExtractError, DownloadError) as err:
            log.error("❌ %s", str(err))
        finally:
            log.info("")


def run():
    app(prog_name=APPNAME)


if __name__ == "__main__":
    run()
