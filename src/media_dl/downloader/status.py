import time
from loguru import logger
from media_dl.downloader.progress import DownloadProgress
from media_dl.models.progress.status import ProcessingState, ProgressState
from media_dl.models.stream import LazyStream


class ProgressCallback(DownloadProgress):
    def __init__(self, disable: bool = False) -> None:
        super().__init__(disable)

        self.task_id = self.add_task(
            description="",
            status="",
            step="",
        )

        self.id = ""
        self.display_name = ""

    def __call__(self, progress: ProgressState):
        match progress.status:
            case "extracting":
                self.update_info(progress.stream)
                self.update(
                    self.task_id,
                    description=self.display_name or "Extracting[blink]...[/]",
                    status="Extracting[blink]...[/]",
                )
                self.log_debug("Resolving Stream")
            case "resolved":
                self.update_info(progress.stream)
                self.update(
                    self.task_id,
                    description=self.display_name,
                    status="Ready",
                )
                self.log_debug("Stream resolved")
            case "skipped":
                logger.info(
                    'Skipped: "{stream}" (Exists as "{extension}").',
                    stream=self.display_name,
                    extension=progress.filepath.suffix[1:],
                )
            case "downloading":
                self.update(
                    self.task_id,
                    completed=progress.downloaded_bytes,
                    total=progress.total_bytes,
                    status="Downloading",
                )
            case "processing":
                self.update(self.task_id, status="Processing[blink]...[/]")
                self.processor_callback(progress)
            case "error":
                logger.error(
                    'Error: "{stream}": {error}',
                    stream=self.display_name,
                    error=progress.message,
                )
            case "completed":
                self.log_debug(
                    'Final file saved in: "{filepath}"',
                    filepath=progress.filepath,
                )
                logger.info('Completed: "{stream}".', stream=self.display_name)

        if progress.status in ("error", "skipped", "completed"):
            self.update(self.task_id, status=progress.status.capitalize())

            self.counter.advance()
            time.sleep(1.0)
            self.remove_task(self.task_id)

    def processor_callback(self, progress: ProcessingState):
        match progress.processor:
            case "remux":
                self.log_debug(
                    'File remuxed as "{extension}"',
                    extension=progress.extension,
                )
            case "embed_subtitles":
                self.log_debug(
                    'Subtitles embedded in: "{file}"',
                    file=progress.filepath,
                )
            case "embed_thumbnail":
                self.log_debug(
                    'Thumbnail embedded in: "{file}"',
                    file=progress.filepath,
                )
            case "embed_metadata":
                self.log_debug(
                    'Metadata embedded in: "{file}"',
                    file=progress.filepath,
                )

    def log_debug(self, log: str, **kwargs):
        text = f'"{self.id}": {log}'
        logger.debug(text, **kwargs)

    def update_info(self, stream: LazyStream):
        self.id = stream.id
        self.display_name = self._stream_display_name(stream)

    def _stream_display_name(self, stream: LazyStream) -> str:
        """Get pretty representation of stream name."""

        if stream.is_music and stream.uploader and stream.title:
            return stream.title + " - " + stream.uploader
        elif stream.title:
            return stream.title
        else:
            return ""
