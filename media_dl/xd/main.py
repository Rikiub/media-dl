from typing import Annotated
from pathlib import Path
import sys

from typer import Typer, Option

from media_dl.config import APPNAME, MAX_THREADS


app = Typer(no_args_is_help=True)

rc = app.registered_commands
rc.extend(download.app.registered_commands)
rc.extend(search.app.registered_commands)


@app.callback()
def common(
    threads: Annotated[
        int,
        Option(
            "--threads",
            "-t",
            max=8,
            help="Number of threads to use when downloading.",
        ),
    ] = MAX_THREADS,
    debug: Annotated[bool, Option("--debug", help="Enable debug mode.")] = False,
):
    if not debug:
        sys.tracebacklimit = 0


def run() -> None:
    app(prog_name=APPNAME.lower())
