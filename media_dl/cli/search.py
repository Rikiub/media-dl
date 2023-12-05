from typer import Typer, Argument, Option, BadParameter
from typing import Annotated
from pathlib import Path

from rich.live import Live
from rich.panel import Panel

from ..theme import *
from ._ui import check_ydl_formats
from ..config import DIR_DOWNLOAD, DIR_TEMP
from ..meta import get_song_list, song_to_file
from ..helper._yt_dlp import YDL

app = Typer()


@app.command()
def search(
    query: Annotated[str, Argument(help="Query to search.", show_default=False)],
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
    extension: Annotated[
        str,
        Option(
            "-x",
            "--extension",
            help="Prefered file extension.",
            callback=check_ydl_formats,
        ),
    ] = "m4a",
):
    with Live(console=console) as live:
        live.update(Panel("Fetching song metadata..."))
        if song := get_song_list(query, limit=1):
            song = song[0]
        else:
            raise BadParameter("Failed.")

        ydl = YDL(quiet=True, cachedir=DIR_TEMP)
        file_query = f"{song.artists[0]} - {song.title}"

        live.update(Panel("Fetching file..."))
        if data := ydl.extract_info_from_search(
            query=file_query, provider="soundcloud"
        ):
            ydl_opts = ydl._generate_ydl_opts(output, extension)
            file_path = ydl._prepare_filename(data[0], ydl_opts)
            ydl.download_multiple(data, extension=extension, output=output)

            live.update(Panel("Parsing metadata..."))

            song_to_file(file_path, song)
        else:
            raise BadParameter("Failed.")
