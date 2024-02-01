from dataclasses import dataclass

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
from media_dl.ydl import (
    YDL,
    Media,
    Playlist,
    DownloadError,
)


@dataclass(slots=True, frozen=True)
class QueueTask:
    url: str
    task_id: TaskID


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


class DownloadWorker:
    urls: list[str]

    def __init__(self, output, extension, quality) -> None:
        self.ydl = YDL(
            output=output,
            extension=extension,  # type: ignore
            quality=quality,  # type: ignore
            exist_ok=False,
        )

    def url_to_result(self, task: QueueTask):
        try:
            result = self.ydl.extract_url(task.url)
            if not result:
                raise DownloadError("_")
        except DownloadError:
            UIProgress.queue.update(
                task.task_id,
                completed=100,
                description=f"[status.error][bold strike]{task.url}",
            )
