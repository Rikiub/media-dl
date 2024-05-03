from typing import Callable
from pathlib import Path
import tempfile

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as YTDLPDownloadError

from media_dl._ydl import OPTS_BASE, DIR_TEMP, format_except_msg
from media_dl.exceptions import DownloadError
from media_dl.models.format import Format


DownloadCallback = Callable[[int, int], None]


class DownloadFormat:
    """Internal downloader.

    Args:
        format: Remote file to download.
        callbacks: List of functions to get download progress information.

    Raises:
        DownloadError: Download failed.
    """

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

        tempname = Path(tempfile.mktemp(dir=DIR_TEMP))
        params = OPTS_BASE | progress | {"outtmpl": str(tempname) + ".%(ext)s"}

        info_dict = {
            "extractor": "generic",
            "extractor_key": "Generic",
            "title": tempname.stem,
            "id": tempname.stem,
            "formats": [self.format._format_dict()],
            "format_id": self.format.id,
        }

        try:
            with YoutubeDL(params) as ydl:
                info = ydl.process_ie_result(info_dict, download=True)
        except YTDLPDownloadError as err:
            msg = format_except_msg(err)
            raise DownloadError(msg)

        if self._callbacks:
            [
                callback(self._total_filesize, self._total_filesize)
                for callback in self._callbacks
            ]

        # Extract final path
        path = info["requested_downloads"][0]["filepath"]

        return Path(path)

    def _progress_wraper(
        self,
        d: dict,
        callback: DownloadCallback,
    ) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        completed: int = d.get("downloaded_bytes") or 0
        total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        if total > self._total_filesize:
            self._total_filesize = total
        if completed > self._downloaded:
            self._downloaded = completed

            callback(self._downloaded, self._total_filesize)
