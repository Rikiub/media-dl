from typing import Annotated
from pathlib import Path
from enum import Enum
import sys

from typer import Typer, Argument, Option

from media_dl.downloader import Downloader
from media_dl.config import APPNAME
from media_dl.types import FORMAT
from media_dl.theme import *

app = Typer(no_args_is_help=True)


class Format(Enum):
    video = "video"
    audio = "audio"


class Provider(Enum):
    ytmusic = "ytmusic"
    soundcloud = "soundcloud"


@app.command(name="download", help="Download from supported URL.", no_args_is_help=True)
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
            show_default=False,
            prompt="What format you want?",
        ),
    ],
    output: Annotated[
        Path,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            file_okay=False,
            resolve_path=True,
            show_default=False,
        ),
    ] = Path.cwd(),
    video_res: Annotated[
        str,
        Option(
            "--video-quality",
            "-qv",
            help="Prefered video resolution. If selected quality is'nt available, closest one is used instead.",
            rich_help_panel="Output",
            min=1,
            max=9,
        ),
    ] = "",
    threads: Annotated[
        int,
        Option(
            "--threads",
            help="Max process.",
        ),
    ] = 4,
    convert: Annotated[
        str,
        Option(
            "--convert",
            help="Convert final file to wanted extension (Slow process).",
            rich_help_panel="Conversion (Advanced)",
        ),
    ] = "",
    quality: Annotated[
        int,
        Option(
            "--audio-quality",
            help="Prefered audio quality when do a file conversion.",
            rich_help_panel="Conversion (Advanced)",
            show_default=False,
            min=1,
            max=9,
        ),
    ] = 9,
    debug: Annotated[bool, Option("--debug", help="Enable debug mode.")] = False,
):
    if not debug:
        sys.tracebacklimit = 0

    fmt: FORMAT = format.value

    dl = Downloader(
        output,
        fmt,
        threads=threads,
        convert=convert,
        video_res=video_res,
        audio_quality=quality,
    )

    for url in urls:
        dl.download([url])


def run() -> None:
    app(prog_name=APPNAME.lower())


if __name__ == "__main__":
    run()
