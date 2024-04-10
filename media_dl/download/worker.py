from typing import Callable, Literal
from pathlib import Path
import tempfile
import logging

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as YTDLPDownloadError

from media_dl.models.format import Format
from media_dl.helper import OPTS_BASE, DIR_TEMP, better_exception_msg
from media_dl.exceptions import DownloadError

log = logging.getLogger(__name__)

PROGRESS_STATUS = Literal[
    "downloading",
    "finished",
    "error",
]
ProgressCallback = Callable[[PROGRESS_STATUS, int, int], None]


class FormatWorker:
    def __init__(
        self,
        format: Format,
        on_progress: ProgressCallback | None = None,
    ):
        self._callback = on_progress

        self.format = format

        self.downloaded = 0
        self.total_filesize = 0

    def start(self) -> Path:
        """Start download of the instance."""

        log.debug(
            "Downloading format %s (%s %s) (%s)",
            self.format.id,
            self.format.extension,
            self.format.display_quality,
            self.format.type,
        )

        # Reset progress
        self.downloaded = 0
        self.total_filesize = 0

        if c := self._callback:
            wrapper = lambda d: self._progress_wraper(d, c)
            progress = {"progress_hooks": [wrapper]}
        else:
            progress = {}

        try:
            format_id = {"format": self.format.id}
            params = (
                OPTS_BASE
                | format_id
                | progress
                | {"outtmpl": tempfile.mktemp(dir=DIR_TEMP) + ".%(ext)s"}
            )

            # Download with complete stream info-dict.
            with YoutubeDL(params) as ydl:
                info = ydl.process_ie_result(
                    self.format._simple_format_dict(), download=True
                )

            # Extract final file path
            path = info["requested_downloads"][0]["filepath"]

            if self._callback:
                self._callback("finished", self.total_filesize, self.total_filesize)

            return Path(path)
        except YTDLPDownloadError as err:
            msg = better_exception_msg(str(err))

            if self._callback:
                self._callback("error", self.downloaded, self.total_filesize)

            raise DownloadError(msg)

    def _progress_wraper(
        self,
        d: dict,
        callback: ProgressCallback,
    ) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        completed: int = d.get("downloaded_bytes") or 0
        total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        if completed > self.downloaded:
            self.downloaded = completed
        if total > self.total_filesize:
            self.total_filesize = total

        callback("downloading", self.downloaded, self.total_filesize)
