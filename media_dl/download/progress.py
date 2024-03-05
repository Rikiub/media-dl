from __future__ import annotations

import time

from rich.console import Group
from rich.table import Column
from rich.live import Live
from rich.progress import (
    MofNCompleteColumn,
    DownloadColumn,
    TextColumn,
    BarColumn,
    Progress,
)

__all__ = ["ProgressHandler"]


class CounterProgress:
    def __init__(self, disable: bool = False) -> None:
        self.disable = disable

        self.overall_completed = 0
        self.overall_total = 0

        self._progress = Progress(
            TextColumn("Total:"),
            MofNCompleteColumn(),
            disable=disable,
        )
        self._task_id = self._progress.add_task("", start=False)

    def advance(self, advance: int = 1):
        self.overall_completed += advance
        self.update()

    def set_total(self, number: int):
        self.overall_total = number
        self.update()

    def reset(self):
        self.overall_completed = 0
        self.overall_total = 0
        self.update()

    def update(self):
        if not self.disable:
            self._progress.update(
                self._task_id,
                total=self.overall_total,
                completed=self.overall_completed,
            )


class ProgressTask:
    def __init__(
        self,
        progress: Progress,
        counter: CounterProgress,
        title: str,
    ):
        __slots__ = [
            "message",
            "status",
            "completed",
            "total",
            "started",
            "progress",
            "counter",
            "task_id",
        ]

        self.message: str = title
        self.status: str = "Starting"
        self.completed: int = 0
        self.total: int = 100

        self.started = False

        self.progress = progress
        self.counter = counter

        self.task_id = self.progress.add_task(
            self.message,
            status=self.status,
            start=False,
            visible=True,
        )

    def update(self):
        if not self.started:
            self.initialize()

        self.progress.update(
            self.task_id,
            description=self.message,
            status=self.status,
            completed=self.completed,
            total=self.total,
        )

    def finalize(self):
        self.counter.advance(1)
        self.progress.remove_task(self.task_id)

    def initialize(self):
        self.progress.start_task(self.task_id)
        self.progress.update(self.task_id, visible=True)
        self.started = True

    def ydl_progress_hook(self, status, downloaded, total):
        match status:
            case "downloading":
                self.status = "Downloading"
                self.completed = downloaded
                self.total = total
            case "processing":
                self.status = "Finishing"
            case "converting":
                self.status = "Converting"
            case "finished":
                self.status = "Done"
            case "error":
                self.status = "Error"

        self.update()

        if status in ("converting", "processing", "finished"):
            if self.completed == 0:
                self.completed = 100
                self.total = 100
                self.update()

        if status in ("error", "finished"):
            time.sleep(1.5)
            self.finalize()


class ProgressHandler:
    """Start and render progress bar."""

    def __init__(self, disable=False) -> None:
        self.disable = disable

        self.counter = CounterProgress(disable=disable)
        self._rich_progress = Progress(
            TextColumn(
                "[white]{task.description}",
                table_column=Column(
                    justify="left",
                    width=40,
                    no_wrap=True,
                    overflow="ellipsis",
                ),
            ),
            TextColumn(
                "[progress.percentage]{task.fields[status]}",
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
            disable=disable,
        )
        self._render_group = Group(self.counter._progress, self._rich_progress)
        self._live = Live()

    def __enter__(self):
        self.start()

    def __exit__(self, a, b, c):
        self.counter.reset()
        self.stop()

    def start(self):
        if not self.disable:
            self._live.update(self._render_group)
            self._live.start()

    def stop(self):
        if not self.disable:
            self._live.update("")
            self._live.stop()

    def create_task(self, title: str) -> ProgressTask:
        return ProgressTask(self._rich_progress, self.counter, title)
