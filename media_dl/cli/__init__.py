from typer import Typer

from ..config import APPNAME
from . import download, meta, search


def run() -> None:
    app = Typer(no_args_is_help=True)

    app.command(name="download", help="Download operations.", no_args_is_help=True)(
        download.download
    )
    app.command(
        name="search",
        help="Search and download Music.",
        no_args_is_help=True,
    )(search.search)
    app.command(
        name="meta",
        help="View/Parse metadata to audio file from multiple Music Providers.",
        no_args_is_help=True,
    )(meta.meta)

    app(prog_name=APPNAME.lower())
