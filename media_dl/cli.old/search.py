from typer import Typer, Argument
from typing import Annotated
from pathlib import Path
from enum import Enum

from media_dl.search import YoutubeSearch
import media_dl.cli._options as opts
from media_dl.config import DIR_DOWNLOAD
from media_dl.downloader import Downloader
from media_dl.types import FORMAT

app = Typer()


class Provider(Enum):
    ytmusic = "ytmusic"
    soundcloud = "soundcloud"


"""
provider: Annotated[
    Provider,
    Option(
        "--provider",
        "-p",
        help="Where get the results. Default: ytmusic",
        show_default=False,
    ),
] = Provider.ytmusic,
"""


@app.command(
    name="search",
    help="Search and download from various music providers.",
    no_args_is_help=True,
)
def search(
    query: Annotated[str, Argument(help="Search term.", show_default=False)],
    format: opts.FormatOption,
    output: opts.OutputOptional = Path.cwd(),
):
    fmt = format.value

    prov = YoutubeSearch()
    dl = Downloader(output, fmt)

    if info := prov.search(query, "ytmusic"):
        info = info[0]
        dl.download([info])
