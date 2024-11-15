from __future__ import annotations

from rich.table import Column
from rich.progress import (
    BarColumn,
    FileSizeColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TotalFileSizeColumn,
)
from rich.console import Group, RenderableType

from media_dl.rich import CONSOLE


class CounterProgress:
    def __init__(
        self, total: int = 1, disable: bool = False, visible: bool = True
    ) -> None:
        self.disable = disable

        self._progress = Progress(
            TextColumn("Total:"),
            MofNCompleteColumn(),
            transient=True,
            expand=False,
            disable=self.disable,
            console=CONSOLE,
        )
        self._task_id = self._progress.add_task(
            "", visible=visible, completed=0, total=total
        )

    def reset(self, total: int = 1, visible: bool = True):
        self._progress.reset(self._task_id, total=total, visible=visible)

    def advance(self, advance: int = 1):
        self._progress.advance(self._task_id, advance)

    def __rich__(self) -> RenderableType:
        return self._progress.get_renderable()


class DownloadProgress(Progress):
    """Start and render progress bar."""

    def __init__(self, disable: bool = False) -> None:
        self.counter = CounterProgress(disable=disable)
        super().__init__(
            TextColumn(
                "{task.description}",
                table_column=Column(ratio=5, no_wrap=True, overflow="ellipsis"),
            ),
            TextColumn(
                "[turquoise2]{task.fields[status]} {task.fields[step]}",
                table_column=Column(ratio=2, no_wrap=True),
            ),
            BarColumn(table_column=Column(justify="full", ratio=4)),
            FileSizeColumn(),
            TextColumn("/"),
            TotalFileSizeColumn(),
            transient=True,
            expand=True,
            disable=disable,
            console=CONSOLE,
        )

    def __enter__(self) -> DownloadProgress:
        super().__enter__()
        return self

    def get_renderable(self) -> RenderableType:
        renderable = Group(self.counter, *self.get_renderables())
        return renderable
