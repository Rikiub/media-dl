from typer import Typer

from media_dl.config import APPNAME
from media_dl.cli import download, search


def run() -> None:
    app = Typer(no_args_is_help=True)

    app.command(
        name="download",
        help="Download operations.",
        no_args_is_help=True,
    )(download.download)

    app.command(
        name="search",
        help="Search from YTMusic and SoundCloud.",
        no_args_is_help=True,
    )(search.search)

    app(prog_name=APPNAME.lower())
