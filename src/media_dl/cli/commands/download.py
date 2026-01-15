from enum import Enum
from pathlib import Path
from typing import Annotated

from loguru import logger
from typer import Argument, BadParameter, Option, Typer

from media_dl.cli.completions import (
    complete_output,
    complete_query,
    complete_resolution,
    parse_queries,
)
from media_dl.cli.config import CONFIG
from media_dl.cli.rich import Status
from media_dl.types import FILE_FORMAT


class HelpPanel(str, Enum):
    file = "File"
    downloader = "Downloader"


app = Typer()


@app.command(no_args_is_help=True)
def download(
    query: Annotated[
        list[str],
        Argument(
            help="""[green]URLs[/] and [green]queries[/] to process.
            \n
            - Insert a [green]URL[/] to download [grey62](Default)[/].\n
            - Select a [green]SERVICE[/] to search and download.
            """,
            show_default=False,
            autocompletion=complete_query,
            metavar="URL | SERVICE",
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
    threads: Annotated[
        int,
        Option(
            "--threads",
            help="Limit of simultaneous downloads.",
            rich_help_panel=HelpPanel.downloader,
        ),
    ] = 5,
    ffmpeg_path: Annotated[
        Path | None,
        Option(
            help="FFmpeg executable to use.",
            rich_help_panel=HelpPanel.downloader,
            show_default=False,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    cache: Annotated[
        bool,
        Option(
            help="Process without use the cache.",
            show_default=False,
            hidden=True,
        ),
    ] = False,
):
    """Download video/audio from [green]URL[/] or search [green]SERVICE[/]."""

    # Lazy Import
    with Status("Starting[blink]...[/]"):
        from media_dl import (
            DownloadError,
            ExtractError,
            MediaDownloader,
            extract_search,
            extract_url,
        )

    # Initialize Downloader
    try:
        downloader = MediaDownloader(
            format=format,
            quality=quality,
            output=output,
            threads=threads,
            use_cache=cache,
            ffmpeg_path=ffmpeg_path,
        )
    except FileNotFoundError as err:
        raise BadParameter(str(err))

    if downloader.config.convert and not downloader.config.ffmpeg_path:
        logger.warning(
            "❗ FFmpeg not installed. File conversion and metadata embeding will be disabled."
        )

    for target, entry in parse_queries(query):
        try:
            with Status("Please wait[blink]...[/]"):
                if target == "url":
                    logger.info('🔎 Extract URL: "{url}".', url=entry)
                    result = extract_url(entry)

                    if result.type == "playlist":
                        logger.info('🔎 Playlist title: "{title}".', title=result.title)
                else:
                    logger.info(
                        '🔎 Search from {extractor}: "{query}".',
                        extractor=target,
                        query=entry,
                    )

                    result = extract_search(
                        entry,
                        target,
                        use_cache=cache,
                    )
                    result = result.medias

            if CONFIG.quiet:
                downloader.download_all(result, None)
            else:
                downloader.download_all(result)

            logger.info("✅ Download Finished.")
        except (ExtractError, DownloadError) as err:
            logger.error("❌ {error}", error=str(err))
        finally:
            logger.info("")
