from typing import Callable, Literal
from threading import Thread, Semaphore
import time

from yt_dlp import YoutubeDL, DownloadError
from rich.table import Column
from rich.progress import (
    DownloadColumn,
    TextColumn,
    BarColumn,
    Progress,
)

from media_dl.extractor import ExtractionError, Extractor
from media_dl.types.download import DownloadConfig
from media_dl.types.models import InfoDict, Media, ResultType
from media_dl.config.theme import *

ProgressCallback = Callable[
    [Literal["downloading", "processing", "finished", "error"], str, int, int],
    None,
]


class DownloadWorker(Thread):
    def __init__(
        self,
        media: Media,
        config: DownloadConfig | None = None,
        callback: ProgressCallback | None = None,
        limiter: Semaphore = Semaphore(),
    ):
        self._extr = Extractor()

        self.media = media
        self.config = config if config else DownloadConfig("video")
        self.callback = callback
        self.loop = limiter

        super().__init__(daemon=True)

    def _callback_wraper(
        self,
        d: dict,
        progress: ProgressCallback,
    ) -> None:
        status = d["status"]
        completed = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        post = d.get("postprocessor") or "DownloadPart"

        match status:
            case "downloading":
                pass
            case "started" | "finished":
                status = "processing"

        progress(status, post, completed, total)

    def resolve_media(self) -> InfoDict:
        self.media, data = self._extr.update_media(self.media)
        return data

    def download(self) -> None:
        if self.callback:
            callback = self.callback
            wrapper = lambda d: self._callback_wraper(d, callback)
            progress = {
                "progress_hooks": [wrapper],
                "postprocessor_hooks": [wrapper],
            }
        else:
            progress = {}

        try:
            info = self.resolve_media()

            with YoutubeDL(self.config.gen_opts() | progress) as ydl:
                data = ydl.process_ie_result(info, download=True)

            path = data["requested_downloads"][0]["filename"]

            if self.callback:
                self.callback("finished", path, 0, 0)
        except (DownloadError, ExtractionError) as err:
            if self.callback:
                self.callback("error", str(err), 0, 0)

    def run(self) -> None:
        self.loop.acquire()
        self.download()
        self.loop.release()


class RichDownloadWorker(DownloadWorker):
    def __init__(
        self,
        media: Media,
        progress: Progress,
        config: DownloadConfig | None = None,
        limiter: Semaphore = Semaphore(),
    ):
        super().__init__(media, config, self.default_callback, limiter)

        self.task_id = progress.add_task(
            self.media_str,
            total=None,
            start=False,
            visible=False,
        )
        self.progress = progress

    @property
    def media_str(self):
        return (
            f"[meta.creator]{self.media.creator}[/] - [meta.title]{self.media.title}[/]"
        )

    def default_callback(self, status, action, completed, total):
        match status:
            case "downloading":
                self.update_text(self.media_str)
                self.update_progress(completed, total)
            case "processing":
                self.update_text("[status.wait][bold]Processing step: " + action)
            case "error":
                self.update_text("[status.error]" + action)
                time.sleep(1.5)
                self.remove_progress()
            case "finished":
                self.update_text("[status.success]Completed")
                time.sleep(1.5)
                self.remove_progress()

    def resolve_media(self) -> InfoDict:
        info = super().resolve_media()
        self.update_text(self.media_str)
        return info

    def update_text(self, text: str):
        self.progress.update(self.task_id, description=text)

    def update_progress(self, completed: int, total: int):
        self.progress.update(self.task_id, completed=completed, total=total)

    def remove_progress(self):
        self.progress.remove_task(self.task_id)

    def init_progress(self):
        self.progress.start_task(self.task_id)
        self.progress.update(self.task_id, visible=True)

    def download(self):
        self.init_progress()
        super().download()


class Downloader:
    def __init__(
        self,
        data: ResultType,
        config: DownloadConfig | None = None,
        threads: int = 4,
    ):
        self.data = data
        self.config = config
        self.loop = Semaphore(threads)

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

    def start(self) -> None:
        if isinstance(self.data, Media):
            d = [self.data]
        else:
            d = self.data

        with self.progress:
            threads = []

            for entry in d:
                t = RichDownloadWorker(
                    entry, self.progress, self.config, limiter=self.loop
                )
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
