from __future__ import annotations

from rich.console import Group, RenderableType
from rich.table import Column
from rich.progress import (
    MofNCompleteColumn,
    DownloadColumn,
    TextColumn,
    BarColumn,
    Progress,
)


class _CounterProgress:
    def __init__(self, total: int = 1, disable: bool = False) -> None:
        self.disable = disable

        self._progress = Progress(
            TextColumn("Total:"),
            MofNCompleteColumn(),
            transient=True,
            expand=False,
            disable=self.disable,
        )
        self._task_id = self._progress.add_task(
            "", start=False, completed=0, total=total
        )

    def advance(self, advance: int = 1):
        self._progress.advance(self._task_id, advance)

    def reset(self, total: int = 1):
        self._progress.reset(self._task_id, total=total)

    def __rich__(self) -> RenderableType:
        return self._progress.get_renderable()


class DownloadProgress(Progress):
    """Start and render progress bar."""

    def __init__(self, count_total: int = 1, disable: bool = False) -> None:
        self.counter = _CounterProgress(total=count_total, disable=disable)
        super().__init__(
            TextColumn(
                "{task.description}",
                table_column=Column(
                    justify="left",
                    width=40,
                    no_wrap=True,
                    overflow="ellipsis",
                ),
            ),
            TextColumn(
                "[turquoise2]{task.fields[status]}",
                table_column=Column(
                    justify="right",
                    width=15,
                    no_wrap=True,
                    overflow="ellipsis",
                ),
            ),
            BarColumn(table_column=Column(justify="right", width=25)),
            DownloadColumn(table_column=Column(justify="right", width=10)),
            transient=True,
            expand=True,
            disable=disable,
        )

    def __enter__(self) -> DownloadProgress:
        super().__enter__()
        return self

    def stop(self):
        self.clean()
        super().stop()

    def clean(self):
        if not self.disable:
            self.counter.reset()

            for task_id in self.task_ids:
                self.remove_task(task_id)

    def get_renderable(self) -> RenderableType:
        renderable = Group(self.counter, *self.get_renderables())
        return renderable
