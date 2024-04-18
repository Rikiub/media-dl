from typing import Callable
from pathlib import Path
import tempfile
import logging

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as YTDLPDownloadError

from media_dl._ydl import OPTS_BASE, DIR_TEMP, format_except_msg
from media_dl.exceptions import DownloadError
from media_dl.models.format import Format


log = logging.getLogger(__name__)

DownloadCallback = Callable[[int, int], None]


class FormatWorker:
    def __init__(
        self,
        format: Format,
        callbacks: list[DownloadCallback] | None = None,
    ):
        self._downloaded = 0
        self._total_filesize = 0
        self._callbacks = callbacks

        self.format = format

    def start(self) -> Path:
        """Start download."""

        log.debug(
            "Downloading format %s (%s %s) (%s)",
            self.format.id,
            self.format.extension,
            self.format.display_quality,
            self.format.type,
        )

        # Reset progress
        self._downloaded = 0
        self._total_filesize = 0

        if self._callbacks:
            wrap = [
                lambda d: self._progress_wraper(d, callback)
                for callback in self._callbacks
            ]
            progress = {"progress_hooks": wrap}
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

            return Path(path)
        except YTDLPDownloadError as err:
            msg = format_except_msg(err)
            raise DownloadError(msg)

    def _progress_wraper(
        self,
        d: dict,
        callback: DownloadCallback,
    ) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        status = d.get("status")
        completed: int = d.get("downloaded_bytes") or 0
        total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        if total > self._total_filesize:
            self._total_filesize = total
        if completed > self._downloaded:
            self._downloaded = completed

            callback(
                self._downloaded if status != "finished" else self._total_filesize,
                self._total_filesize,
            )
