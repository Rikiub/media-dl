from typing import Callable, cast
from pathlib import Path
import tempfile

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as YTDLPDownloadError

from media_dl._ydl import OPTS_BASE, DIR_TEMP, format_except_msg, InfoDict
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
        self.format = format

        self.downloaded = 0
        self.total_filesize = 0

        self._callbacks = callbacks

    def run(self) -> Path:
        """Start format download.

        Returns:
            Filepath to temporary file.
        """

        self.reset_progress()

        if self._callbacks:
            wrappers = [
                lambda d: self._progress_wraper(d, callback)
                for callback in self._callbacks
            ]
            progress = {"progress_hooks": wrappers}
        else:
            progress = {}

        temp_path = Path(tempfile.mktemp(dir=DIR_TEMP))

        params = OPTS_BASE | progress | {"outtmpl": str(temp_path) + ".%(ext)s"}
        info_dict = {
            "extractor": "generic",
            "extractor_key": "Generic",
            "title": temp_path.stem,
            "id": temp_path.stem,
            "formats": [self.format._format_dict()],
            "format_id": self.format.id,
        }

        info = self._download(info_dict, params)

        if self._callbacks:
            [
                callback(self.total_filesize, self.total_filesize)
                for callback in self._callbacks
            ]

        path = info["requested_downloads"][0]["filepath"]
        return Path(path)

    def reset_progress(self):
        self.downloaded = 0
        self.total_filesize = 0

    def _download(self, info, params) -> InfoDict:
        try:
            with YoutubeDL(params) as ydl:
                info = ydl.process_ie_result(info, download=True)
                return cast(InfoDict, info)
        except YTDLPDownloadError as err:
            msg = format_except_msg(err)
            raise DownloadError(msg)

    def _progress_wraper(
        self,
        d: dict,
        callback: DownloadCallback,
    ) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        completed: int = d.get("downloaded_bytes") or 0
        total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        if total > self.total_filesize:
            self.total_filesize = total
        if completed > self.downloaded:
            self.downloaded = completed

            callback(self.downloaded, self.total_filesize)
