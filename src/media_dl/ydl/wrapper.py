import logging

from yt_dlp.YoutubeDL import YoutubeDL

from media_dl.ydl.types import YDLParams


class YTDLP(YoutubeDL):
    """Custom `YoutubeDL` which supress output."""

    _SUPRESS_LOGGER = logging.getLogger("YoutubeDL")
    _SUPRESS_LOGGER.disabled = True

    def __init__(self, params: YDLParams | None = None, auto_init: bool = False):
        # Default parameters
        opts: YDLParams = {
            "logger": self._SUPRESS_LOGGER,  # type: ignore
            "ignoreerrors": False,
            "consoletitle": False,
            "no_warnings": True,
            "noprogress": True,
            "quiet": True,
            "trim_file_name": 150,
            "color": {"stdout": "no_color", "stderr": "no_color"},
        }

        # Custom parameters
        opts |= params or {}

        # Initialize
        super().__init__(
            opts,  # type: ignore
            auto_init,
        )
