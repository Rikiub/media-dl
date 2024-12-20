"""yt-dlp parameters, functions and constans used around the project."""

import logging
from enum import Enum
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.metadataparser import MetadataParserPP
from yt_dlp.utils import MEDIA_EXTENSIONS

from media_dl.types import InfoDict, StrPath


class SupportedExtensions(frozenset[str], Enum):
    """Sets of file extensions supported by YT-DLP."""

    video = frozenset(MEDIA_EXTENSIONS.video)
    audio = frozenset(MEDIA_EXTENSIONS.audio)


ThumbnailSupport = frozenset(
    {
        "mp3",
        "mkv",
        "mka",
        "ogg",
        "opus",
        "flac",
        "m4a",
        "mp4",
        "m4v",
        "mov",
    }
)


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

        # Init
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


# Helpers
def run_postproces(file: Path, info: InfoDict, params: dict) -> Path:
    """Postprocess file by params."""

    info = YTDLP(params).post_process(filename=str(file), info=info)
    return Path(info["filepath"])


def parse_output_template(info: InfoDict, template: str) -> str:
    """Get a custom filename by output template."""

    return YTDLP().prepare_filename(info, outtmpl=template)


def download_thumbnail(filepath: StrPath, info: InfoDict) -> Path | None:
    ydl = YTDLP(
        {
            "writethumbnail": True,
            "outtmpl": {
                "thumbnail": "",
                "pl_thumbnail": "",
            },
        }
    )

    final = ydl._write_thumbnails(
        label=filepath, info_dict=info, filename=str(filepath)
    )

    if final:
        return Path(final[0][0])
    else:
        return None


def download_subtitle(filepath: StrPath, info: InfoDict) -> Path | None:
    ydl = YTDLP({"writesubtitles": True, "allsubtitles": True})

    subs = ydl.process_subtitles(
        filepath, info.get("subtitles"), info.get("automatic_captions")
    )
    info |= {"requested_subtitles": subs}

    final = ydl._write_subtitles(info_dict=info, filename=str(filepath))

    if final:
        return Path(final[0][0])
    else:
        return None


def format_except_message(exception: Exception) -> str:
    """Get a user friendly message of a YT-DLP message exception."""

    msg = str(exception)

    # No connection
    if "HTTP Error" in msg:
        msg = (
            msg
            + " : You may have exceeded the page request limit, received an IP block, among others. Please try again later."
        )

    elif "Read timed out" in msg:
        msg = "Read timed out."

    elif any(s in msg for s in ("[Errno -3]", "Failed to extract any player response")):
        msg = "No internet connection."

    # Invalid URL
    elif "Unable to download webpage" in msg and any(
        s in msg for s in ("[Errno -2]", "[Errno -5]")
    ):
        msg = "Invalid URL."

    elif "is not a valid URL" in msg:
        splits = msg.split()
        msg = splits[1] + " is not a valid URL."

    elif "Unsupported URL" in msg:
        splits = msg.split()
        msg = "Unsupported URL: " + splits[3]

    elif "Unable to extract webpage video data" in msg:
        msg = "Unable to extract webpage video data."

    # Postprocessing
    elif "Unable to rename file" in msg:
        msg = "Unable to rename file."

    elif "ffmpeg not found" in msg:
        msg = "Postprocessing failed. FFmpeg executable not founded."

    # General
    elif "No video formats found!" in msg:
        msg = "No formats founded."

    elif any(s in msg for s in ("Unable to download", "Got error")):
        msg = "Unable to download."

    elif "is only available for registered users" in msg:
        msg = "Only available for registered users."

    # Last parse
    if msg.startswith("ERROR: "):
        msg = msg.strip("ERROR: ")

    return msg
