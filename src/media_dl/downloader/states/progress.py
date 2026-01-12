from dataclasses import dataclass
import time
from loguru import logger
from rich.progress import TaskID
from media_dl.downloader.progress import DownloadProgress
from media_dl.models.progress.states import ProcessingState, ProgressState
from media_dl.models.stream import LazyStream


@dataclass(slots=True)
class Task:
    task_id: TaskID
    id: str
    name: str


class ProgressCallback(DownloadProgress):
    def __init__(self, disable: bool = False) -> None:
        super().__init__(disable)
        self.ids: dict[str, Task] = {}

    def __call__(self, progress: ProgressState):
        match progress.status:
            case "extracting":
                item = self.ids[progress.id] = Task(
                    task_id=self.add_task(
                        description="",
                        status="",
                        step="",
                    ),
                    id=progress.id,
                    name=self._stream_display_name(progress.stream),
                )

                self.update(
                    self.get(progress).task_id,
                    description=item.name or "Extracting[blink]...[/]",
                    status="Extracting[blink]...[/]",
                )
            case "resolved":
                name = self.ids[progress.id].name = self._stream_display_name(
                    progress.stream
                )

                self.update(
                    self.get(progress).task_id,
                    description=name,
                    status="Ready",
                )
            case "skipped":
                logger.info(
                    'Skipped: "{stream}" (Exists as "{extension}").',
                    stream=self.get(progress).name,
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
                    'Error: "{stream}": {error}',
                    stream=self.get(progress).name,
                    error=progress.message,
                )
            case "completed":
                logger.info('Completed: "{stream}".', stream=self.get(progress).name)

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

    def get(self, progress: ProgressState):
        return self.ids[progress.id]

    def advance_counter(self, progress: ProgressState, delay: float):
        self.counter.advance()
        time.sleep(delay)
        self.remove_task(self.get(progress).task_id)

    def log_debug(self, id: str, log: str, **kwargs):
        text = f'"{id}": {log}'
        logger.debug(text, **kwargs)

    def _stream_display_name(self, stream: LazyStream) -> str:
        """Get pretty representation of stream name."""

        if stream.is_music and stream.uploader and stream.title:
            return stream.title + " - " + stream.uploader
        elif stream.title:
            return stream.title
        else:
            return ""
