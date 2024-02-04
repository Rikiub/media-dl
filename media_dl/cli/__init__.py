from typer import Typer, Option
from typing import Annotated
from pathlib import Path

from media_dl.config import APPNAME, DIR_DOWNLOAD, MAX_THREADS
from media_dl.cli import download, search

app = Typer(no_args_is_help=True)

app.command(
    name="download",
    help="Download from supported URL.",
    no_args_is_help=True,
)(download.download)

app.command(
    name="search",
    help="Search and download from various music providers.",
    no_args_is_help=True,
)(search.search)


@app.callback()
def common(
    output: Annotated[
        Path,
        Option(
            "-o",
            "--output",
            help="Directory where to save downloads.",
            file_okay=False,
            resolve_path=True,
        ),
    ] = DIR_DOWNLOAD,
    threads: Annotated[
        int,
        Option(
            "-t",
            "--threads",
            max=8,
            help="Number of threads to use when downloading.",
        ),
    ] = MAX_THREADS,
):
    DIR_DOWNLOAD = output
    MAX_THREADS = threads


def run() -> None:
    app(prog_name=APPNAME.lower())
