from typing import Annotated, Literal, get_args
from pathlib import Path

from typer import Typer, Argument, Option
from strenum import StrEnum

from media_dl.types.formats import SEARCH_PROVIDER, EXTENSION, FORMAT
from media_dl.downloader.base import DownloaderError
from media_dl.extractor import ExtractionError
from media_dl.config.dirs import APPNAME
from media_dl.config.theme import print
from media_dl import YDL, FormatConfig

app = Typer()

Format = StrEnum("Format", get_args(Literal[FORMAT, EXTENSION]))
Provider = StrEnum("Provider", get_args(Literal[SEARCH_PROVIDER, "url"]))


class HelpPanel(StrEnum):
    mode = "Mode"
    formatting = "Formatting"
    other = "Others"


@app.command(no_args_is_help=True)
def download(
    query: Annotated[
        list[str],
        Argument(
            help="URLs or queries to process and download.",
            show_default=False,
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
            rich_help_panel=HelpPanel.mode,
            show_default=False,
        ),
    ],
    search: Annotated[
        Provider,
        Option(
            "--search-from",
            "-s",
            help="Switch to search mode from selected provider.",
            rich_help_panel=HelpPanel.mode,
        ),
    ] = Provider["url"],
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
    video_res: Annotated[
        int,
        Option(
            "--video-quality",
            "-vq",
            help="Prefered video resolution when request a video file.",
            metavar="RESOLUTION {480-720-1080}",
            rich_help_panel=HelpPanel.formatting,
        ),
    ] = 720,
    audio_quality: Annotated[
        int,
        Option(
            "--audio-quality",
            "-aq",
            help="Prefered audio quality when do a file conversion.",
            metavar="BITRATE {128-256-320}",
            rich_help_panel=HelpPanel.formatting,
        ),
    ] = 9,
    threads: Annotated[
        int,
        Option(
            "--threads",
            help="Max parallels process to execute.",
            rich_help_panel=HelpPanel.other,
        ),
    ] = 4,
    quiet: Annotated[
        bool,
        Option(
            "--quiet", "-q", help="Supress output.", rich_help_panel=HelpPanel.other
        ),
    ] = False,
):
    """
    yt-dlp helper with nice defaults ✨.
    """

    ydl = YDL(
        config=FormatConfig(
            format=format.value,
            video_quality=video_res,
            audio_quality=audio_quality,
            output=output,
        ),
        threads=threads,
        quiet=quiet,
    )

    for url in query:
        if not quiet:
            print()
            print(f"[status.work][Processing]: [green]'{url}'")

        try:
            if search != "url":
                info = ydl.extract_from_search(url, search.value)
                info = info[0]
            else:
                info = ydl.extract_from_url(url)

            if not info:
                raise ExtractionError(f"'{url}' is invalid or unsupported.")

            ydl.download(info)
        except (ExtractionError, DownloaderError) as err:
            msg = str(err)

            if not quiet:
                print("[status.work][Error]: [status.error]" + msg)

            continue
        else:
            if not quiet:
                print(f"[status.work][Done]: {url}")


def run():
    app(prog_name=APPNAME.lower())


if __name__ == "__main__":
    run()
