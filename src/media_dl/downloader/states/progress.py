import time
from dataclasses import dataclass

from loguru import logger
from rich.progress import TaskID

from media_dl.downloader.progress import DownloadProgress
from media_dl.models.content.media import LazyMedia
from media_dl.models.progress.media import MediaDownloadState, ProcessingState


@dataclass(slots=True)
class Task:
    task_id: TaskID
    id: str
    name: str


class ProgressCallback(DownloadProgress):
    def __init__(self, disable: bool = False) -> None:
        super().__init__(disable)
        self.ids: dict[str, Task] = {}

    def __call__(self, progress: MediaDownloadState):
        match progress.status:
            case "resolving":
                item = self.ids[progress.id] = Task(
                    task_id=self.add_task(
                        description="",
                        status="",
                        step="",
                    ),
                    id=progress.id,
                    name=self._media_display_name(progress.media),
                )

                self.update(
                    self.get(progress).task_id,
                    description=item.name or "Extracting[blink]...[/]",
                    status="Extracting[blink]...[/]",
                )
            case "resolved":
                name = self.ids[progress.id].name = self._media_display_name(
                    progress.media
                )

                self.update(
                    self.get(progress).task_id,
                    description=name,
                    status="Ready",
                )
            case "skipped":
                logger.info(
                    'Skipped: "{media}" (Exists as "{extension}").',
                    media=self.get(progress).name,
                    extension=progress.extension,
                )

                self.update(self.get(progress).task_id, status="Skipped")
                self.advance_counter(progress, 0.6)
            case "downloading":
                self.update(
                    self.get(progress).task_id,
                    completed=progress.downloaded_bytes,
                    total=progress.total_bytes,
                    status="Downloading",
                )
            case "processing":
                self.processor_callback(progress)
            case "error":
                logger.error(
                    'Error: "{media}": {error}',
                    media=self.get(progress).name,
                    error=progress.message,
                )
            case "completed":
                logger.info('Completed: "{media}".', media=self.get(progress).name)

        if progress.status in ("error", "completed"):
            self.update(self.get(progress).task_id, status=progress.status.capitalize())
            self.advance_counter(progress, 1.0)

    def processor_callback(self, progress: ProcessingState):
        if progress.processor == "starting":
            self.update(
                self.get(progress).task_id,
                status="Processing[blink]...[/]",
            )

        match progress.processor:
            case "convert_audio":
                if progress.stage == "started":
                    self.update(
                        self.get(progress).task_id,
                        status="Converting[blink]...[/]",
                    )

    def get(self, progress: MediaDownloadState):
        return self.ids[progress.id]

    def advance_counter(self, progress: MediaDownloadState, delay: float):
        self.counter.advance()
        time.sleep(delay)
        self.remove_task(self.get(progress).task_id)

    def log_debug(self, id: str, log: str, **kwargs):
        text = f'"{id}": {log}'
        logger.debug(text, **kwargs)

    def _media_display_name(self, media: LazyMedia) -> str:
        """Get pretty representation of media name."""

        if media.is_music and media.uploader and media.title:
            return media.title + " - " + media.uploader
        elif media.title:
            return media.title
        else:
            return ""
