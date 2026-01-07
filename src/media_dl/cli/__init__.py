from typer import Typer

from media_dl.cli.arguments.download import app as download
from media_dl.cli.arguments.extract import app as extract

from media_dl.cli.utils.options import VerboseOption, QuietOption, VersionOption
from media_dl.types import APPNAME
from media_dl.logging import init_logging

app = Typer(no_args_is_help=True, rich_markup_mode="rich")
app.add_typer(download)
app.add_typer(extract)


@app.callback()
def main(
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    version: VersionOption = False,
):
    if quiet:
        log_level = "CRITICAL"
    elif verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"

    init_logging(log_level)


def run():
    app(prog_name=APPNAME)
