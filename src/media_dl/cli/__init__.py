from typer import Typer

from media_dl.cli.commands import download, main
from media_dl.types import APPNAME

app = Typer(
    callback=main.main,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(download.app)


def run():
    app(prog_name=APPNAME)
