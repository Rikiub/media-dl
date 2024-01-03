from typer import Typer

from media_dl.config import APPNAME
from media_dl.cli import download


def run() -> None:
    app = Typer(no_args_is_help=True)

    app.command(
        name="download",
        help="Download operations.",
        no_args_is_help=True,
    )

    app(prog_name=APPNAME.lower())
