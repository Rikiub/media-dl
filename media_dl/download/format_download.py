from typing import Callable, Literal
from threading import Event
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as _DownloaderError

from media_dl.ydl_base import BASE_OPTS, DOWNLOAD_OPTS, better_exception_msg
from media_dl.download.format_config import FormatConfig
from media_dl.models.format import Format

PROGRESS_STATUS = Literal["downloading", "processing", "finished", "error"]
ProgressCallback = Callable[[PROGRESS_STATUS, str, int, int], None]


class DownloaderError(Exception):
    pass


class FormatDownloader:
    def __init__(
        self,
        format: Format,
        config: FormatConfig | None = None,
        on_progress: ProgressCallback | None = None,
        event: Event | None = None,
    ):
        # Save and resolve config to match with provided format.
        self.config = config if config else FormatConfig(format.type)
        self.config.format = self.config.target_convert or format.type

        self.format = format

        self._event = event if event else Event()
        self._callback = on_progress

    def start(self) -> None:
        if self._event.is_set():
            return
        self.run()

    def run(self) -> str:
        if c := self._callback:
            wrapper = lambda d: self._callback_wraper(d, c)
            progress = {
                "progress_hooks": [wrapper],
                # "postprocessor_hooks": [wrapper],
            }
        else:
            progress = {}

        try:
            fmt = {"format": self.format.format_id}
            params = BASE_OPTS | DOWNLOAD_OPTS | self.config.gen_opts() | fmt | progress

            with YoutubeDL(params) as ydl:
                data = ydl.process_ie_result(self.format.get_info(), download=True)

            path = data["requested_downloads"][0]["filepath"]

            if self._callback:
                self._callback("finished", path, 0, 0)

            return path
        except _DownloaderError as err:
            msg = better_exception_msg(str(err), self.format.url)

            if self._callback:
                self._callback("error", msg, 0, 0)

            raise DownloaderError(msg)

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
                status = "downloading"
            case "started" | "finished":
                status = "processing"

        progress(status, action, completed, total)
