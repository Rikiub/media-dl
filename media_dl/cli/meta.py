from typing import Annotated
from pathlib import Path

from rich.live import Live
from rich.panel import Panel
from rich.console import Group
from rich.pretty import Pretty
from rich.prompt import IntPrompt, Confirm
from rich.progress import (
    Progress,
    TextColumn,
    SpinnerColumn,
)
from typer import Typer, Argument, Option, BadParameter

from media_dl.theme import *
from media_dl.meta import get_song_list, song_to_file, file_to_song, Song

app = Typer()


def spinner_progress(text: str) -> Progress:
    spinner_progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )
    spinner_progress.add_task(text, total=None)
    return spinner_progress


@app.command()
def meta(
    file: Annotated[
        Path,
        Argument(
            help="File to view. Add --query to search metadata",
            show_default=False,
            resolve_path=True,
            exists=True,
        ),
    ],
    query: Annotated[
        str, Option("-q", "--query", help="Query to search.", show_default=False)
    ] = "",
    limit: Annotated[
        int, Option("-l", "--limit", help="Number of searchs to do.", min=1)
    ] = 5,
    skip: Annotated[
        bool, Option("-s", "--skip", help="Just process the first result.")
    ] = False,
):
    song_list: list[Song] = []

    if not query:
        song = file_to_song(file)

        print(
            Panel(
                Pretty(song, max_string=75),
                title="Song",
                border_style="status.warn",
                expand=False,
            )
        )
    else:
        with Live(console=console) as live:
            live.update(
                Panel(
                    spinner_progress("[bold]Fetching data..."),
                    border_style="status.work",
                )
            )

            try:
                if songs := get_song_list(query, providers=["spotify"], limit=limit):
                    song_list = songs
                    live.update("")
                elif not songs:
                    raise ConnectionError
            except ConnectionError:
                raise BadParameter("Failed to fetch songs.")

        print(
            Panel(
                f'Modifing file [text.label][bold underline]"{file.name}"',
                border_style="status.warn",
            )
        )

        if skip:
            song = song_list[0]
        else:
            panels: list[Panel] = []
            panels_index = []
            for i, song in enumerate(song_list, start=1):
                panels.append(
                    Panel(
                        f"[status.work][{i}][/] [text.meta.uploader]{song.artists[0]}[/] - [text.meta.title]{song.title}[/]"
                    )
                )
                panels_index.append(i)
            print(Group(*panels))

            selected = IntPrompt().ask(
                "[status.work][bold italic]Select metadata",
                console=console,
                show_choices=False,
                choices=[str(x) for x in panels_index],
            )
            song = song_list[selected - 1]

            print(
                Panel(
                    Pretty(song, max_string=75),
                    title="Selected",
                    border_style="status.warn",
                    expand=False,
                )
            )
            if Confirm().ask("[status.work][bold]Continue?", console=console):
                pass
            else:
                raise SystemExit

        print(
            Panel(
                f'Parsing "[text.meta.uploader]{song.artists[0]}[/] - [text.meta.title]{song.title}[/]" to file [text.label][bold underline]"{file.name}"',
                border_style="status.work",
            )
        )
        song_to_file(file, song)

        if not skip and file.stem != f"{song.artists[0]} - {song.title}":
            if selected := Confirm().ask(
                "[status.work][bold]Rename file?", console=console
            ):
                new_file = Path(f"{song.artists[0]} - {song.title}{file.suffix}")

                if new_file.is_file():
                    print(
                        Panel(
                            f'The file [text.label][bold underline]"{new_file.name}"[/] yet exists.',
                            border_style="status.error",
                        )
                    )
                else:
                    file.rename(new_file.name)

        print(Panel(f"[bold]Completed", border_style="status.success"))
