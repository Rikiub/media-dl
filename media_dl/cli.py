from typing import Annotated
from pathlib import Path
from enum import Enum
import sys

from typer import Typer, Argument, Option

from media_dl.downloader import Downloader
from media_dl.config import APPNAME
from media_dl.theme import *

app = Typer(rich_markup_mode="rich")


class Format(Enum):
    video = "video"
    audio = "audio"


class RichPanel:
    output = "Formatting"
    search = "Search"
    convert = "Conversion (Advanced)"
    dev = "Others (Advanced)"


@app.command(
    name="download",
    help="[green]yt-dlp[/] helper with [italic green]nice defaults[/].",
    no_args_is_help=True,
)
def download(
    urls: Annotated[
        list[str], Argument(help="URL(s) to download.", show_default=False)
    ],
    format: Annotated[
        Format,
        Option(
            "--format",
            "-f",
            help="File type to request. Would fallback to 'audio' if 'video' is not available.",
            prompt="What format you want?",
            rich_help_panel=RichPanel.output,
            show_default=False,
        ),
    ],
    search: Annotated[
        str,
        Option(
            "--search-from",
            "-s",
            help="Switch to 'search' mode from selected provider.",
            rich_help_panel=RichPanel.output,
        ),
    ] = "",
    video_res: Annotated[
        str,
        Option(
            "--video-quality",
            "-r",
            help="Prefered video resolution. If selected quality is'nt available, closest one is used instead.",
            rich_help_panel=RichPanel.output,
            min=1,
            max=9,
        ),
    ] = "",
    output: Annotated[
        Path,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            rich_help_panel=RichPanel.output,
            file_okay=False,
            resolve_path=True,
            show_default=False,
        ),
    ] = Path.cwd(),
    convert: Annotated[
        str,
        Option(
            "--convert",
            help="Convert final file to wanted extension (Slow process).",
            rich_help_panel=RichPanel.convert,
        ),
    ] = "",
    audio_quality: Annotated[
        int,
        Option(
            "--audio-quality",
            help="Prefered audio quality when do a file conversion.",
            rich_help_panel=RichPanel.convert,
            show_default=False,
            min=1,
            max=9,
        ),
    ] = 9,
    threads: Annotated[
        int,
        Option(
            "--threads", help="Max process to execute.", rich_help_panel=RichPanel.dev
        ),
    ] = 4,
    debug: Annotated[
        bool,
        Option("--debug", help="Enable debug mode.", rich_help_panel=RichPanel.dev),
    ] = False,
):
    if not debug:
        sys.tracebacklimit = 0

    dl = Downloader(
        output,
        format.value,
        threads=threads,
        convert=convert,
        video_res=video_res,
        audio_quality=audio_quality,
    )

    if search:
        for url in urls:
            if info := dl.ydl.search(url, search):  # type: ignore
                info = info[0]
                dl.download(info)
    else:
        dl.download(urls)


def run() -> None:
    app(prog_name=APPNAME.lower())


if __name__ == "__main__":
    run()
