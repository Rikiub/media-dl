from dataclasses import dataclass
import time
from loguru import logger
from rich.progress import TaskID
from media_dl.downloader.progress import DownloadProgress
from media_dl.models.progress.state import ProcessingState, ProgressState
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
                self.log_debug(progress.id, "Resolving Stream")
            case "resolved":
                name = self.ids[progress.id].name = self._stream_display_name(
                    progress.stream
                )

                self.update(
                    self.get(progress).task_id,
                    description=name,
                    status="Ready",
                )
                self.log_debug(progress.id, "Stream resolved")
            case "skipped":
                logger.info(
                    'Skipped: "{stream}" (Exists as "{extension}").',
                    stream=self.get(progress).name,
                    extension=progress.filepath.suffix[1:],
                )
            case "downloading":
                self.update(
                    self.get(progress).task_id,
                    completed=progress.downloaded_bytes,
                    total=progress.total_bytes,
                    status="Downloading",
                )
            case "processing":
                self.update(
                    self.get(progress).task_id,
                    status="Processing[blink]...[/]",
                )
                self.processor_callback(progress)
            case "error":
                logger.error(
                    'Error: "{stream}": {error}',
                    stream=self.get(progress).name,
                    error=progress.message,
                )
            case "completed":
                self.log_debug(
                    self.get(progress).id,
                    'Final file saved in: "{filepath}"',
                    filepath=progress.filepath,
                )
                logger.info('Completed: "{stream}".', stream=self.get(progress).name)

        if progress.status in ("error", "skipped", "completed"):
            self.update(self.get(progress).task_id, status=progress.status.capitalize())

            self.counter.advance()
            time.sleep(1.0)
            self.remove_task(self.get(progress).task_id)

    def processor_callback(self, progress: ProcessingState):
        match progress.processor:
            case "remux":
                self.log_debug(
                    progress.id,
                    'File remuxed as "{extension}"',
                    extension=progress.extension,
                )
            case "embed_subtitles":
                self.log_debug(
                    progress.id,
                    'Subtitles embedded in: "{file}"',
                    file=progress.filepath,
                )
            case "embed_thumbnail":
                self.log_debug(
                    progress.id,
                    'Thumbnail embedded in: "{file}"',
                    file=progress.filepath,
                )
            case "embed_metadata":
                self.log_debug(
                    progress.id,
                    'Metadata embedded in: "{file}"',
                    file=progress.filepath,
                )

    def get(self, progress: ProgressState):
        return self.ids[progress.id]

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
