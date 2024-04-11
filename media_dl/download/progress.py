from __future__ import annotations

from rich.console import Group
from rich.table import Column
from rich.live import Live
from rich.progress import (
    MofNCompleteColumn,
    DownloadColumn,
    TaskID,
    TextColumn,
    BarColumn,
    Progress,
)

__all__ = ["ProgressHandler"]


class CounterProgress(Group):
    def __init__(self, disable: bool = False) -> None:
        self.disable = disable

        self.completed = 0
        self.total = 1

        self._progress = Progress(
            TextColumn("Total:"),
            MofNCompleteColumn(),
            disable=self.disable,
        )
        self._task_id = self._progress.add_task(
            "", start=False, completed=self.completed, total=self.total
        )

        super().__init__(self._progress)

    def advance(self, advance: int = 1):
        self.completed += advance
        self.update()

    def set_total(self, total: int):
        self.total = total
        self.update()

    def reset(self):
        self.completed = 0
        self.total = 1
        self.update()

    def update(self):
        if not self.disable:
            self._progress.update(
                self._task_id,
                total=self.total,
                completed=self.completed,
            )


class ProgressHandler(Group):
    """Start and render progress bar."""

    def __init__(self, disable=False) -> None:
        self.disable = disable
        self.live = Live()

        self.counter = CounterProgress(disable=self.disable)
        self._progress = Progress(
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
            transient=False,
            expand=True,
            disable=self.disable,
        )
        super().__init__(self.counter, self._progress)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, a, b, c):
        self.clean()
        self.stop()

    def start(self):
        if not self.disable:
            self.live.update(self)
            self.live.start(refresh=True)

    def stop(self):
        if not self.disable:
            self.live.update("")
            self.live.stop()

    def clean(self):
        if not self.disable:
            self.counter.reset()

            for task_id in self._progress.task_ids:
                self._progress.remove_task(task_id)

    def update(self, task_id: TaskID, **kwargs):
        self._progress.update(task_id, **kwargs)

    def add_task(self, description: str, status: str, **kwargs) -> TaskID:
        return self._progress.add_task(
            description=description, status=status, total=None, **kwargs
        )

    def remove_task(self, task_id: TaskID) -> None:
        self._progress.remove_task(task_id)
