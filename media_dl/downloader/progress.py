import time

from rich.table import Column
from rich.progress import (
    DownloadColumn,
    TextColumn,
    BarColumn,
    Progress,
)

from media_dl.config.theme import CONSOLE
from media_dl.downloader.base import (
    DLWork,
    FormatConfig,
    Media,
    Event,
    InfoDict,
    BaseDownloader,
    ResultType,
)


class RichDLWork(DLWork):
    def __init__(
        self,
        media: Media,
        progress: Progress,
        config: FormatConfig | None = None,
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


class DownloaderProgress(BaseDownloader):
    def __init__(
        self,
        config: FormatConfig | None = None,
        max_threads: int = 4,
        error_limit: int = 4,
        render: bool = True,
    ):
        super().__init__(
            config=config,
            max_threads=max_threads,
            error_limit=error_limit,
        )

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
        self._render = render

        if not self._render:
            self._progress.disable = True

    def _worker_callback(self, data: list[Media]) -> list[DLWork]:
        return [
            RichDLWork(
                task,
                self._progress,
                config=self._config,
                event=self._event,
            )
            for task in data
        ]

    def _reset_progress(self) -> None:
        for task_id in self._progress.task_ids:
            self._progress.remove_task(task_id)

    def get_rich_progress(self) -> Progress:
        return self._progress

    def download(self, data: ResultType) -> None:
        func = super().download

        try:
            if self._render:
                with self._progress:
                    func(data)
            else:
                func(data)
        finally:
            self._reset_progress()
