from typer import Typer

from media_dl.cli.arguments import download

from media_dl.cli.utils.options import VerboseOption, QuietOption, VersionOption
from media_dl.types import APPNAME
from media_dl.logging import init_logging

app = Typer(no_args_is_help=True, rich_markup_mode="rich")


@app.callback()
def main(
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    version: VersionOption = False,
):
    """Download any video/audio you want from a simple URL ✨"""

    if quiet:
        log_level = "CRITICAL"
    elif verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"

    init_logging(log_level)


app.add_typer(download.app)
# app.add_typer(extract)


def run():
    app(prog_name=APPNAME)
