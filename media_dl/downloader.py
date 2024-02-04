from dataclasses import dataclass
from pathlib import Path
import threading
import time

from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.table import Column
from rich.console import Group, RenderableType
from rich.markdown import HorizontalRule
from rich.progress import (
    MofNCompleteColumn,
    DownloadColumn,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    Progress,
)

from media_dl.theme import *
from media_dl.types import Media, Playlist, ResultType
from media_dl.ydl import (
    YDL,
    DownloadError,
)

semaphore = threading.Semaphore(3)


class CounterComp:
    def __init__(self, text: str) -> None:
        self.progress = Progress(
            TextColumn(
                "[progress.percentage]{task.description}",
            ),
            MofNCompleteColumn(),
            console=console,
        )
        self.task_id = self.progress.add_task(text, total=None)

    @property
    def render(self) -> Progress:
        return self.progress

    def advance(self):
        self.progress.advance(self.task_id, 1)

    def reset(self):
        self.progress.update(self.task_id, total=None, completed=None)

    def set_limit(self, limit: int):
        self.progress.update(self.task_id, total=limit)


class DownloadWorker(threading.Thread):
    def __init__(self, ydl: YDL, progress: Progress, media: Media):
        self.ydl = ydl
        self.media = media

        self.task_id = progress.add_task(
            self.media_str,
            start=False,
            visible=False,
        )
        self.progress = progress

        super().__init__(daemon=True)

    @property
    def media_str(self):
        return (
            f"[meta.creator]{self.media.creator}[/] - [meta.title]{self.media.title}[/]"
        )

    def _ydl_progress_hook(self, d):
        match d["status"]:
            case "downloading":
                downloaded_bytes = d.get("downloaded_bytes")
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                self.progress.update(
                    self.task_id,
                    completed=downloaded_bytes,
                    total=total_bytes,
                )
            case "finished":
                self.update_text("[status.wait][bold]Converting" + "[blink]...")

    def update_text(self, text: str):
        self.progress.update(self.task_id, description=text)

    def update_media(self):
        self.update_text("[blink][status.wait]...")

        result = self.ydl.extract_url(self.media.url)

        if isinstance(result, Media):
            self.media = result

        self.update_text(self.media_str)

    def init_progressbar(self):
        self.progress.start_task(self.task_id)
        self.progress.update(self.task_id, visible=True)

    def run(self) -> None:
        semaphore.acquire()

        try:
            self.init_progressbar()

            if not self.media.is_complete():
                self.update_media()

            self.ydl.download(self.media, progress_callback=self._ydl_progress_hook)
            self.update_text("[status.success]Completed")
        except DownloadError as err:
            self.update_text("[status.error][bold]" + str(err.msg))
        finally:
            time.sleep(1.5)
            self.progress.remove_task(self.task_id)
            semaphore.release()


class Downloader:
    def __init__(self, *args, threads: int = 4, **kwargs) -> None:
        self._ydl = YDL(*args, **kwargs)
        self.threads = threads
        self.queue = []

        # Progress Bars
        self.progress = Progress(
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

        self.counter = CounterComp("[text.label][bold]Counter:")

    @staticmethod
    def get_loading_bar() -> Progress:
        load = Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        )
        load.add_task(f"[status.work]Loading[blink]...[/]")
        return load

    def create_render(self, result: ResultType) -> RenderableType:
        match result:
            case Playlist():
                self.counter.set_limit(result.count)
                return Group(
                    f"[text.label][bold]Playlist Title:[/][/] [text.desc]{result.title}[/]\n"
                    f"[text.label][bold]Source:[/][/] [text.desc]{result.extractor}[/]",
                    self.counter.render,
                )
            case Media():
                self.counter.set_limit(1)
                return Group(
                    f"[text.label][bold]Media Title:[/][/] [text.desc]{result.title}[/]\n"
                    f"[text.label][bold]Creator:[/][/] [text.desc]{result.creator}[/]\n"
                    f"[text.label][bold]Source:[/][/] [text.desc]{result.extractor}[/]",
                    self.counter.render,
                )
            case _:
                raise TypeError()

    def result_to_iter(self, result: ResultType) -> list[Media]:
        items = []

        if isinstance(result, Playlist):
            items = result.entries
        elif isinstance(result, Media):
            items = [result]

        return items

    def download(self, urls: list[str]) -> None:
        with Live(console=console) as live:
            for url in urls:
                if info := self._ydl.extract_url(url):
                    media_info = self.create_render(info)
                    live.update(Group(media_info, HorizontalRule(), self.progress))

                    threads = []
                    for media in self.result_to_iter(info):
                        t = DownloadWorker(self._ydl, self.progress, media)
                        t.start()
                        threads.append(t)
                    for t in threads:
                        t.join()
                        self.counter.advance()
                self.counter.reset()


if __name__ == "__main__":
    url = "https://gourmetdeluxxx.bandcamp.com/track/nocturnal-hooli"

    dl = Downloader("temp", format="best-audio")
    dl.download([url])
