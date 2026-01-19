try:
    from typer import Typer
except ImportError:
    print("Error: The CLI dependencies are not installed.")
    raise SystemExit(1)

from media_dl.types import APPNAME
from media_cli.commands import download, main

app = Typer(
    callback=main.main,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(download.app)


def run():
    app(prog_name=APPNAME)
