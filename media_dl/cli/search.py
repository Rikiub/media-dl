from typer import Typer, Argument, Option, BadParameter
from typing import Annotated
from pathlib import Path

from rich.live import Live
from rich.panel import Panel

from media_dl.theme import *
from media_dl.ydls import YDL
from media_dl.cli._ui import check_ydl_formats
from media_dl.config import DIR_DOWNLOAD, DIR_TEMP
from media_dl.meta import get_song_list, song_to_file

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

        if song := get_song_list(query, providers=["spotify", "musicbrainz"], limit=1):
            song = song[0]
        else:
            raise BadParameter("Failed.")

        with YDL(quiet=True, tempdir=DIR_TEMP, outputdir=output, ext=extension) as ydl:
            live.update(Panel("Fetching file..."))

            search_query = f"{song.artists[0]} - {song.title}"
            if data := ydl.search_info_from_provider(
                query=search_query, provider="ytmusic"
            ):
                filename = ydl.download_single(data.entries[0])

                live.update(Panel("Parsing metadata..."))

                song_to_file(filename, song)
                filename.rename(filename.with_name(search_query + filename.suffix))
            else:
                raise BadParameter("Failed.")
