import logging

from yt_dlp.postprocessor.metadataparser import MetadataParserPP
from yt_dlp.YoutubeDL import YoutubeDL


class YTDLP(YoutubeDL):
    """Custom `YoutubeDL` which supress output."""

    _SUPRESS_LOGGER = logging.getLogger("YoutubeDL")
    _SUPRESS_LOGGER.disabled = True

    def __init__(self, params: dict | None = None):
        # Default parameters
        opts = {
            "logger": self._SUPRESS_LOGGER,
            "ignoreerrors": False,
            "consoletitle": False,
            "no_warnings": True,
            "noprogress": True,
            "quiet": True,
            "trim_file_name": 150,
            "color": {"stdout": "no_color", "stderr": "no_color"},
            "postprocessors": [
                {
                    "key": "MetadataParser",
                    "when": "pre_process",
                    "actions": [
                        (
                            MetadataParserPP.interpretter,
                            "uploader",
                            "(?P<uploader>.+)(?: - Topic)$",
                        ),
                    ],
                },
            ],
        }

        # Custom parameters
        opts |= params or {}

        # Initialize
        super().__init__(opts)


POST_MUSIC = [
    {
        "key": "MetadataParser",
        "when": "post_process",
        "actions": [
            (
                MetadataParserPP.interpretter,
                "%(track,title)s",
                "%(meta_track)s",
            ),
            (
                MetadataParserPP.interpretter,
                "%(artist,uploader)s",
                "%(meta_artist)s",
            ),
            (
                MetadataParserPP.interpretter,
                "%(album,title)s",
                "%(meta_album)s",
            ),
            (
                MetadataParserPP.interpretter,
                "%(album_artist,uploader)s",
                "%(meta_album_artist)s",
            ),
            (
                MetadataParserPP.interpretter,
                "%(release_year,release_date>%Y,upload_date>%Y)s",
                "%(meta_date)s",
            ),
        ],
    }
]
