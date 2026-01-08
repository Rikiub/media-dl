from loguru import logger
from pathlib import Path
from typer import Typer, BadParameter, Argument, Option
from typing import Annotated

from media_dl.cli.utils.completions import (
    complete_query,
    complete_resolution,
    complete_output,
    parse_queries,
)
from media_dl.rich import Status
from media_dl.cli.utils.options import QuietOption
from media_dl.cli.utils.sections import HelpPanel
from media_dl.types import FILE_FORMAT

app = Typer()


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
        FILE_FORMAT,
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
    ] = "video",
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
            help="Limit of simultaneous downloads.",
            rich_help_panel=HelpPanel.downloader,
        ),
    ] = 5,
    quiet: QuietOption = False,
):
    """Download any video/audio you want from a simple URL ✨"""

    # Lazy Import
    with Status("Starting...", disable=quiet):
        from media_dl.downloader.stream import StreamDownloader
        from media_dl.exceptions import DownloadError, ExtractError
        from media_dl.models.playlist import SearchQuery
        from media_dl.cli.utils.helpers import extract_query

    # Initialize Downloader
    try:
        downloader = StreamDownloader(
            format=format,
            quality=quality,
            output=output,
            ffmpeg=ffmpeg,
            threads=threads,
            show_progress=not quiet,
        )
    except FileNotFoundError as err:
        raise BadParameter(str(err))

    if downloader.config.convert and not downloader.config.ffmpeg:
        logger.warning(
            "❗ FFmpeg not installed. File conversion and metadata embeding will be disabled."
        )

    for target, entry in parse_queries(query):
        try:
            result = extract_query(target, entry, quiet)
            if isinstance(result, SearchQuery):
                result = result.streams[0]

            downloader.download_all(result)
            logger.info("✅ Download Finished.")
        except (ExtractError, DownloadError) as err:
            logger.error("❌ {error}", error=str(err))
        finally:
            logger.info("")
