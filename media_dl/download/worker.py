from typing import Callable, Literal, cast
from pathlib import Path
import logging

from yt_dlp import YoutubeDL
from yt_dlp import DownloadError as _DownloadError

from media_dl.models.stream import Stream
from media_dl.models.format import Format

from media_dl.helper import BASE_OPTS, better_exception_msg, MUSIC_SITES, InfoDict
from media_dl.download.config import FormatConfig

log = logging.getLogger(__name__)

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


class DownloadWorker:
    def __init__(
        self,
        stream: Stream,
        format: Format | None = None,
        config: FormatConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ):
        """`YT-DLP` wrapper and single stream downloader.

        It will download their stream and get a file formatted by provided config.
        The config will be resolved to match with arguments.

        Args:
            stream: Target `Stream` to download.
            format: Specific `Stream` format to download. By default will select the BEST format.

        Raises:
            ValueError: Provided `Format` wasn't founded in the `Stream` formats list.
        """

        __slots__ = (
            "downloaded",
            "total_filesize",
            "stream",
            "format",
            "config",
            "_callback",
        )

        if not stream.formats:
            self.stream = stream.update()
        else:
            self.stream = stream

        self.config = config if config else FormatConfig("video")
        self._callback = on_progress

        # If we have format, should resolve config by format.
        if format:
            if not format in self.stream.formats:
                raise ValueError(f"'{format.id}' format id not founded in Stream.")

            if not self.config.convert:
                self.config.format = format.type

            self.format = format

        # If we haven't format, should resolve format by config
        else:
            # Change config to 'audio' if stream URL is a music site.
            if not self.config.convert:
                for site in MUSIC_SITES:
                    if site in self.stream.url:
                        log.debug(
                            "Detected music site in stream '%s'. Changing config to 'audio'.",
                            self.stream.display_name,
                        )
                        self.config.format = "audio"
                        break

            self.format = self._get_best_format()

            # Match config with requested format.
            if not self.config.convert and self.config.type != self.format.type:
                log.debug(
                    "Format '%s' and Config '%s' missmatch in '%s'. Changing config to '%s'.",
                    self.format.type,
                    self.config.type,
                    self.stream.display_name,
                    self.format.type,
                )

                self.config.format = self.format.type

        self.downloaded = 0
        self.total_filesize = 0

    def start(self) -> Path:
        """Start download of the instance."""

        log.debug(
            "Downloading '%s' with format %s (%s %s) (%s)",
            self.stream.display_name,
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
            progress = {
                "progress_hooks": [wrapper],
                "postprocessor_hooks": [wrapper],
            }
        else:
            progress = {}

        try:
            format_id = {"format": self.format.id}
            params = BASE_OPTS | self.config._gen_opts() | format_id | progress

            # Download with complete stream info-dict.
            with YoutubeDL(params) as ydl:
                try:
                    info = self.stream.get_info_dict()
                    info = ydl.process_ie_result(info, download=True)
                except _DownloadError as msg:
                    if "HTTP Error 403" in str(msg):
                        log.debug(
                            "HTTP Error 403 in '%s'. Retrying again.",
                            self.stream.display_name,
                        )

                        info = ydl.extract_info(self.stream.url, download=True)
                        info = cast(InfoDict, info)
                    else:
                        raise

            # Extract final file path
            path = info["requested_downloads"][0]["filepath"]

            if self._callback:
                self._callback("finished", self.total_filesize, self.total_filesize)

            return Path(path)
        except _DownloadError as err:
            msg = better_exception_msg(str(err))

            if self._callback:
                self._callback("error", self.downloaded, self.total_filesize)

            raise DownloaderError(msg)

    def _progress_wraper(
        self,
        d: dict,
        callback: ProgressCallback,
    ) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        status: PROGRESS_STATUS = d["status"]
        post: str = d.get("postprocessor") or ""
        completed: int = d.get("downloaded_bytes") or 0
        total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        if completed > self.downloaded:
            self.downloaded = completed
        if total > self.total_filesize:
            self.total_filesize = total

        match status:
            case "downloading":
                status = status
            case "finished":
                if self.config.convert:
                    status = "converting"
                else:
                    status = "processing"

        callback(status, self.downloaded, self.total_filesize)

    def _get_best_format(self) -> Format:
        """Resolve and extract the best format in the instance."""

        format_list = self.stream.formats

        # Filter by extension
        if f := self.config.convert and format_list.filter(
            extension=self.config.convert
        ):
            final = f
        # Filter by type
        elif f := format_list.filter(type=self.config.type):
            final = f
        # Filter fallback to available type.
        elif f := format_list.filter(type="video") or format_list.filter(type="audio"):
            final = f
        else:
            raise TypeError("Not matches founded in format list.")

        if self.config.quality:
            return f.get_closest_quality(self.config.quality)
        else:
            return final[-1]
