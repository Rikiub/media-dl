from typing import Callable, Literal
import concurrent.futures as cf
from threading import Event
import time

from yt_dlp import YoutubeDL, DownloadError
from rich.table import Column
from rich.progress import (
    DownloadColumn,
    TextColumn,
    BarColumn,
    Progress,
)

from media_dl.types.models import InfoDict, Media, Playlist, ResultType
from media_dl.extractor import ExtractionError, Extractor
from media_dl.types.download import DownloadConfig
from media_dl.config.theme import CONSOLE

ProgressCallback = Callable[
    [Literal["downloading", "processing", "finished", "error"], str, int, int],
    None,
]


class DownloaderError(Exception):
    pass


class DownloadWork:
    def __init__(
        self,
        media: Media,
        config: DownloadConfig | None = None,
        callback: ProgressCallback | None = None,
        event: Event = Event(),
    ):
        self.media = media
        self.config = config if config else DownloadConfig("video")

        self._extr = Extractor()
        self._callback = callback
        self._event = event

    def _callback_wraper(
        self,
        d: dict,
        progress: ProgressCallback,
    ) -> None:
        status = d["status"]
        post = d.get("postprocessor") or "DownloadPart"
        completed = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        if status == "downloading":
            pass
        elif status in ("started", "finished"):
            status = "processing"

        progress(status, post, completed, total)

    def resolve_media(self) -> InfoDict:
        self.media, data = self._extr.update_media(self.media)
        return data

    def start_download(self) -> bool:
        if c := self._callback:
            wrapper = lambda d: self._callback_wraper(d, c)
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

            if callback := self._callback:
                callback("finished", path, 0, 0)

            return True
        except (DownloadError, ExtractionError) as err:
            if callback := self._callback:
                callback("error", str(err), 0, 0)

            return False

    def run(self) -> bool:
        if self._event.is_set():
            return False
        return self.start_download()


class RichDownloadWork(DownloadWork):
    def __init__(
        self,
        media: Media,
        progress: Progress,
        config: DownloadConfig | None = None,
        event: Event = Event(),
    ):
        super().__init__(
            media=media,
            config=config,
            callback=self.default_callback,
            event=event,
        )

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

    def start_download(self):
        self.init_progress()
        return super().start_download()


class Downloader:
    def __init__(
        self,
        config: DownloadConfig | None = None,
        max_threads: int = 4,
        error_limit: int = 4,
    ):
        self._event = Event()
        self._threads = max_threads
        self._error_limit = error_limit

        self._config = config
        self._progress = Progress(
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
            console=CONSOLE,
        )

    def _resolve_data(self, data: ResultType) -> list[Media]:
        match data:
            case Media():
                return [data]
            case Playlist():
                return data.entries
            case list():
                return data
            case _:
                raise TypeError(data)

    def _init_tasks(self, data: ResultType) -> list[RichDownloadWork]:
        return [
            RichDownloadWork(
                task, self._progress, config=self._config, event=self._event
            )
            for task in self._resolve_data(data)
        ]

    def download(self, data: ResultType) -> None:
        with self._progress:
            with cf.ThreadPoolExecutor(self._threads) as executor:
                futures = [executor.submit(task.run) for task in self._init_tasks(data)]

                sucess = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        result: bool = ft.result()

                        if result:
                            sucess += 1
                        else:
                            errors += 1

                        if errors > self._error_limit:
                            raise DownloaderError("Too many errors to continue.")
                finally:
                    self._event.set()
