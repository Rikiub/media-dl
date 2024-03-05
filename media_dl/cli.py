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
from media_dl.download.format_config import (
    FILE_REQUEST,
    FORMAT_TYPE,
    EXT_VIDEO,
    EXT_AUDIO,
    VIDEO_RES,
)

log = logging.getLogger(__name__)

app = Typer()

Format = StrEnum("Format", get_args(FILE_REQUEST))
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
                msg = f"Did you mean '{completed[0]}'?"
            else:
                msg = "Should be URL or search provider."

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
            
            - To get BEST, select 'video' or 'audio' (Fast).\n
            - To convert, select a file EXTENSION (Slow).
            """,
            metavar=f"""[{'|'.join(get_args(FORMAT_TYPE))}]
[{'|'.join(get_args(EXT_VIDEO))}]
[{'|'.join(get_args(EXT_AUDIO))}]
""",
            prompt="""
What format you want request?

- To get BEST, select 'video' or 'audio' (Fast).
- To convert, select a file EXTENSION (Slow).

""",
            prompt_required=False,
            rich_help_panel=HelpPanel.formatting,
            show_default=False,
        ),
    ] = Format["video"],
    quality: Annotated[
        int,
        Option(
            "--quality",
            help="Prefered video/audio quality to filter.",
            rich_help_panel=HelpPanel.formatting,
            autocompletion=complete_resolution,
            show_default=False,
        ),
    ] = 0,
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
    ffmpeg: Annotated[
        Path,
        Option(
            "--ffmpeg",
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
            format=format.value,
            quality=quality if quality != 0 else None,
            output=output,
            ffmpeg="" if ffmpeg == Path.cwd() else ffmpeg,
            threads=threads,
            quiet=quiet,
        )
    except FileNotFoundError as err:
        log.error(err)
        raise SystemExit(1)

    if not ydl._downloader.config.ffmpeg:
        log.warning(
            "❗ FFmpeg not installed. File conversion and metadata embeding will be disabled.\n"
        )

    for target, entry in parse_input(query):
        try:
            if target.value == "url":
                log.info("🔎 Extracting '%s'", entry)
                result = ydl.extract_url(entry)
            else:
                log.info("🔎 Searching '%s' from '%s'", entry, target.value)
                result = ydl.extract_search(entry, target.value)
                result = result[1]
        except ExtractionError:
            continue

        try:
            ydl.download(result)
        except DownloaderError as err:
            log.error("❌ %s", str(err))
            continue
        else:
            log.info("✅ Done '%s'\n", entry)


def run():
    app(prog_name=APPNAME.lower())


if __name__ == "__main__":
    run()
