from rich.panel import Panel
from rich.align import Align
from rich.table import Column
from rich.console import Group
from rich.markdown import HorizontalRule
from rich.progress import (
    MofNCompleteColumn,
    DownloadColumn,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    Progress,
    TaskID,
)

from media_dl.theme import *


class UIProgress:
    queue = Progress(
        SpinnerColumn(),
        TextColumn(
            "[progress.description]{task.description}",
            table_column=Column(justify="right"),
        ),
        console=console,
    )

    download = Progress(
        TextColumn(
            "[progress.percentage]{task.description}",
            table_column=Column(
                justify="left",
                width=40,
                no_wrap=True,
                overflow="ellipsis",
            ),
        ),
        BarColumn(table_column=Column(justify="center", width=20)),
        DownloadColumn(table_column=Column(justify="right", width=15)),
        transient=True,
        expand=True,
        console=console,
    )

    @staticmethod
    def get_loading_bar() -> Progress:
        load = Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        )
        load.add_task(f"[status.work]Loading[blink]...[/]")
        return load
