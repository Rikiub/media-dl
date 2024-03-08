from typing import Callable, Literal
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as _DownloaderError

from media_dl.models.stream import Stream
from media_dl.helper import better_exception_msg
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
        meta_stream: Stream | None = None,
        config: FormatConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ):
        """
        Download a format and get file formatted by provided config.
        If a stream is provided would format its filename and embed extra metadata like thumbnail and subtitles.
        """

        self.format = format
        self.stream = meta_stream
        self.config = config if config else FormatConfig(format.type)

        self.downloaded = 0
        self.total_filesize = 0

        # Resolve config to match with requested format.
        conf_type = self.config.type
        conf_ext = self.config.convert

        if conf_ext and conf_ext != self.format.extension:
            self.config.format = conf_ext
        elif conf_type != self.format.type:
            self.config.format = conf_type

        self._callback = on_progress

    def start(self) -> Path:
        # Reset progress
        self.downloaded = 0
        self.total_filesize = 0

        if c := self._callback:
            wrapper = lambda d: self._progress_wraper(d, c)
            progress = {
                "progress_hooks": [wrapper],
                "postprocessor_hooks": [wrapper],
            }
        else:
            progress = {}

        try:
            format_id = {"format": self.format.id}
            params = self.config._gen_opts() | format_id | progress

            with YoutubeDL(params) as ydl:
                try:
                    data = ydl.process_ie_result(
                        self.stream.get_info_dict() if self.stream else {},
                        download=True,
                    )
                except _DownloaderError:
                    data = ydl.process_ie_result(
                        self.format._simple_format_dict(), download=True
                    )

            path = data["requested_downloads"][0]["filepath"]

            if self._callback:
                self._callback("finished", self.total_filesize, self.total_filesize)

            return Path(path)
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

        if completed > self.downloaded:
            self.downloaded = completed
        if total > self.total_filesize:
            self.total_filesize = total

        # Exclude pre-processors hooks
        if post == "MetadataParser":
            return

        match status:
            case "downloading":
                status = status
            case "finished":
                if self.config.convert:
                    status = "converting"
                else:
                    status = "processing"

        callback(status, self.downloaded, self.total_filesize)
