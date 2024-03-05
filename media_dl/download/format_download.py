from typing import Callable, Literal
from threading import Event

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as _DownloaderError

from media_dl.ydl_base import better_exception_msg
from media_dl.download.format_config import FormatConfig
from media_dl.models.format import Format


PROGRESS_STATUS = Literal[
    "downloading",
    "processing",
    "converting",
    "finished",
    "error",
]
ProgressCallback = Callable[[PROGRESS_STATUS, int, int], None]


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
        self.format = format
        self.config = config if config else FormatConfig(format.type)
        self.convert = False

        # Resolve config to match with requested format.
        fmt_type = format.type
        conv_ext = self.config.convert

        if conv_ext and conv_ext != self.format.extension:
            self.config.format = conv_ext
            self.convert = True
        elif fmt_type != format.type:
            self.config.format = fmt_type

        self._event = event if event else Event()
        self._callback = on_progress

    def start(self) -> None:
        if self._event.is_set():
            return
        self.run()

    def run(self) -> str:
        if c := self._callback:
            wrapper = lambda d: self._progress_wraper(d, c)
            progress = {
                "progress_hooks": [wrapper],
                "postprocessor_hooks": [wrapper],
            }
        else:
            progress = {}

        try:
            fmt = {"format": self.format.format_id}
            params = self.config.gen_opts() | fmt | progress

            with YoutubeDL(params) as ydl:
                data = ydl.process_ie_result(self.format.get_info(), download=True)

            path = data["requested_downloads"][0]["filepath"]

            if self._callback:
                self._callback("finished", 0, 0)

            return path
        except _DownloaderError as err:
            msg = better_exception_msg(str(err), self.format.url)

            if self._callback:
                self._callback("error", 0, 0)

            raise DownloaderError(msg)

    def _progress_wraper(
        self,
        d: dict,
        callback: ProgressCallback,
    ) -> None:
        status: PROGRESS_STATUS = d["status"]
        post = d.get("postprocessor") or ""
        completed: int = d.get("downloaded_bytes") or 0
        total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        # Exclude pre-processors hooks
        if post == "MetadataParser":
            return

        match status:
            case "downloading":
                status = status
            case "finished":
                if self.convert:
                    status = "converting"
                else:
                    status = "processing"

        callback(status, completed, total)
