from typing import Callable, Literal
from abc import ABC, abstractmethod
import concurrent.futures as cf
from threading import Event

from yt_dlp import YoutubeDL, DownloadError

from media_dl.extractor import Extractor, ExtractionError, resolve_exception_msg
from media_dl.types.models import InfoDict, Media, ResultType
from media_dl.types.formats import FormatConfig

PROGRESS_STATUS = Literal["downloading", "processing", "finished", "error"]
ProgressCallback = Callable[[PROGRESS_STATUS, str, int, int], None]


class DownloaderError(Exception):
    pass


class DLWork:
    def __init__(
        self,
        media: Media,
        config: FormatConfig | None = None,
        callback: ProgressCallback | None = None,
        event: Event = Event(),
    ):
        """Single item downloader."""

        self.media = media
        self.config = config if config else FormatConfig("best-video")

        self._extr = Extractor()
        self._callback = callback
        self._event = event

    def _callback_wraper(
        self,
        d: dict,
        progress: ProgressCallback,
    ) -> None:
        status: PROGRESS_STATUS = d["status"]
        action: str = d.get("postprocessor") or "DownloadPart"
        completed: int = d.get("downloaded_bytes") or 0
        total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        match status:
            case "downloading":
                pass
            case "started" | "finished":
                status = "processing"

        progress(status, action, completed, total)

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

            if self._callback:
                self._callback("finished", path, 0, 0)

            return True
        except (DownloadError, ExtractionError) as err:
            if self._callback:
                msg = resolve_exception_msg(str(err), self.media.url)
                self._callback("error", msg, 0, 0)

            return False

    def start(self) -> bool:
        if self._event.is_set():
            return False
        return self.start_download()


class BaseDownloader(ABC):
    """Multi-thread interface for download workers."""

    def __init__(
        self,
        config: FormatConfig | None = None,
        max_threads: int = 4,
        error_limit: int = 4,
    ):
        self._config = config
        self._error_limit = error_limit
        self._threads = max_threads
        self._event = Event()

    @abstractmethod
    def _worker_callback(self, data: list[Media]) -> list[DLWork]:
        """
        This method must be overrided in subclasses.

        When run the download function, it will send a list of `Media` to this function.
        You must handle the list and create its respective 'download worker'.
        """

        return [
            DLWork(
                task,
                config=self._config,
                event=self._event,
            )
            for task in data
        ]

    def download(self, data: ResultType) -> None:
        """Start download and process the files with provided format parameters."""

        with cf.ThreadPoolExecutor(self._threads) as executor:
            resolve = Extractor.resolve_result

            futures = [
                executor.submit(task.start)
                for task in self._worker_callback(resolve(data))
            ]

            is_single = True if isinstance(data, Media) else False
            sucess = 0
            errors = 0

            try:
                for ft in cf.as_completed(futures):
                    result: bool = ft.result()

                    if result:
                        sucess += 1
                    else:
                        errors += 1

                    if is_single and errors >= 1:
                        raise DownloaderError("Failed to download.")
                    elif errors > self._error_limit:
                        raise DownloaderError(
                            "Too many errors to continue downloading the playlist."
                        )
            finally:
                self._event.set()
