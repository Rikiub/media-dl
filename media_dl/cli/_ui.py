from dataclasses import dataclass
import threading
import time

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
from media_dl.types import Media, Playlist
from media_dl.ydl import (
    YDL,
    DownloadError,
)

semaphore = threading.Semaphore(3)


class DownloadWork(threading.Thread):
    def __init__(self, ydl: YDL, progress: Progress, media: Media):
        self.ydl = ydl
        self.media = media

        self.task_id = progress.add_task(
            media.creator + " - " + media.title,
            start=False,
            visible=False,
        )
        self.progress = progress
        self.has_filesize = False

        super().__init__(daemon=True)

    def _ydl_progress_hook(self, d):
        match d["status"]:
            case "downloading":
                if not self.has_filesize:
                    self.has_filesize = True
                    total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                    self.progress.update(self.task_id, completed=total_bytes)
                self.progress.update(self.task_id, total=d.get("downloaded_bytes"))
            case "finished":
                self.update_text("[status.wait][bold]Converting" + "[blink]...")

    def update_text(self, text: str):
        self.progress.update(self.task_id, description=text)

    def update_info(self):
        self.progress.update(
            self.task_id, description=self.media.creator + " - " + self.media.title
        )

    def start_progress(self):
        self.progress.start_task(self.task_id)
        self.progress.update(self.task_id, visible=True)

    def run(self) -> None:
        semaphore.acquire()

        try:
            self.start_progress()

            if not self.media.is_complete():
                self.update_text("[blink][status.wait]...")

                if new_media := self.ydl.extract_url(self.media.url):
                    if isinstance(new_media, Media):
                        self.media = new_media  # type: ignore
                        self.update_info()

            self.ydl.download(self.media, progress_callback=self._ydl_progress_hook)
            self.update_text("[status.success]Completed")
        except DownloadError as err:
            self.update_text("[status.error][bold]" + str(err.msg))
        finally:
            time.sleep(1.5)
            self.progress.remove_task(self.task_id)
            semaphore.release()


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


if __name__ == "__main__":
    url = "https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth"

    ydl = YDL("temp", "best-audio")
    progress = UIProgress.download

    with progress:
        if info := ydl.extract_url(url):
            items: list[Media] = []
            threads = []

            if isinstance(info, Playlist):
                for entry in info:
                    items = info.entries
            else:
                items = [info]

            for media in items:
                t = DownloadWork(ydl, progress, media)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
        else:
            print("Sin resultados")
