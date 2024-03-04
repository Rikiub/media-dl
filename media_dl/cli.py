from typing import Annotated, Generator, Literal, get_args
from pathlib import Path
import logging

from typer import Typer, Argument, Option, BadParameter
from strenum import StrEnum

from media_dl import YDL
from media_dl.dirs import APPNAME
from media_dl.logging import init_logging
from media_dl.extractor import ExtractionError, SEARCH_PROVIDER
from media_dl.download import DownloaderError
from media_dl.download.format_config import EXTENSION, FORMAT_TYPE, VIDEO_RES

log = logging.getLogger(__name__)

app = Typer()

Format = StrEnum("Format", get_args(Literal["best-video", "best-audio", EXTENSION]))
SearchFrom = StrEnum("SearchFrom", get_args(Literal["url", SEARCH_PROVIDER]))


class HelpPanel(StrEnum):
    formatting = "Format"
    advanced = "Advanced"


def complete_query(incomplete: str) -> Generator[str, None, None]:
    for name in SearchFrom:
        if name.value.startswith(incomplete):
            yield name.value + ":"


def complete_resolution() -> list[str]:
    return [str(entry) for entry in get_args(VIDEO_RES)]


def parse_format(format: str) -> FORMAT_TYPE:
    if format == "best-video":
        return "video"
    elif format == "best-audio":
        return "only-audio"
    else:
        return format  # type: ignore


def parse_input(queries: list[str]) -> list[tuple[SearchFrom, str]]:
    providers = [entry.name for entry in SearchFrom]
    results = []

    for entry in queries:
        target = entry.split(":")[0]

        if entry.startswith(("http://", "https://")):
            results.append((SearchFrom["url"], entry))

        elif target in providers:
            final = entry.split(":")[1]
            results.append((SearchFrom[target], final))

        else:
            completed = [i for i in complete_query(target)]

            if completed:
                msg = f"Maybe you mean the provider '{completed[0]}'?"
            else:
                msg = "Should be URL or provider."

            raise BadParameter(f"'{target}' is invalid. {msg}")

    return results


@app.command(no_args_is_help=True)
def download(
    query: Annotated[
        list[str],
        Argument(
            help="""URLs and queries to process.
            \n
            - Insert URL to download (Default).\n
            - Select one PROVIDER to search and download.
            """,
            show_default=False,
            autocompletion=complete_query,
            metavar=f"URL | PROVIDER",
        ),
    ],
    format: Annotated[
        Format,
        Option(
            "--format",
            "-f",
            help="""
            File type to request.
            \n
            - To get BEST, select 'best-video' or 'best-audio' (Fast).
            \n
            - To convert, select one file EXTENSION (Slow).
            """,
            metavar="BEST | EXTENSION",
            prompt="""
What format you want request?

- To get BEST, select 'best-video' or 'best-audio' (Fast).
- To convert, select one file EXTENSION (Slow).

""",
            prompt_required=False,
            rich_help_panel=HelpPanel.formatting,
            show_default=False,
        ),
    ] = Format["best-video"],
    output: Annotated[
        Path,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            rich_help_panel=HelpPanel.formatting,
            show_default=False,
            resolve_path=False,
            file_okay=False,
        ),
    ] = Path.cwd(),
    quality: Annotated[
        int,
        Option(
            "--quality",
            help="Prefered video resolution or audio bitrate to filter.",
            metavar="RESOLUTION | BITRATE",
            rich_help_panel=HelpPanel.formatting,
            autocompletion=complete_resolution,
            show_default=False,
        ),
    ] = 0,
    ffmpeg: Annotated[
        Path,
        Option(
            "--ffmpeg-location",
            help="FFmpeg executable to use.",
            rich_help_panel=HelpPanel.advanced,
            show_default=False,
            resolve_path=True,
        ),
    ] = Path.cwd(),
    threads: Annotated[
        int,
        Option(
            "--threads",
            help="Max parallels process to execute.",
            rich_help_panel=HelpPanel.advanced,
        ),
    ] = 4,
    verbose: Annotated[
        bool,
        Option(
            "--verbose",
            help="Display more information on screen. Useful for debugging.",
            rich_help_panel=HelpPanel.advanced,
        ),
    ] = False,
    quiet: Annotated[
        bool,
        Option(
            "--quiet",
            help="Supress screen information.",
            rich_help_panel=HelpPanel.advanced,
        ),
    ] = False,
):
    """
    yt-dlp helper with nice defaults ✨.
    """

    if quiet:
        log_level = logging.CRITICAL
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    init_logging(log_level)

    try:
        ydl = YDL(
            format=parse_format(format.value),
            quality=quality if quality != 0 else None,
            output=output,
            ffmpeg_location="" if ffmpeg == Path.cwd() else ffmpeg,
            threads=threads,
            quiet=quiet,
        )
    except FileNotFoundError as err:
        log.error(err)
        raise SystemExit(1)

    for target, entry in parse_input(query):
        log.info("Processing: %s", entry)

        try:
            if target.value == "url":
                result = ydl.extract_url(entry)
            else:
                result = ydl.extract_search(entry, target.value)
                result = result[1]

            ydl.download(result)
        except (ExtractionError, DownloaderError):
            continue
        else:
            log.info("\nDone: %s", entry)


def run():
    app(prog_name=APPNAME.lower())


if __name__ == "__main__":
    run()
