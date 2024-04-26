"""yt-dlp parameters, functions and constans used around the project."""

from typing import NewType, Any, Literal, cast
from tempfile import mkdtemp
from pathlib import Path
from enum import Enum
import logging
import atexit
import shutil

from yt_dlp import YoutubeDL
from yt_dlp.utils import MEDIA_EXTENSIONS
from yt_dlp.postprocessor.metadataparser import MetadataParserPP


# YTDLP Base
_supress_logger = logging.getLogger("YoutubeDL")
_supress_logger.disabled = True

OPTS_BASE = {
    "logger": _supress_logger,
    "ignoreerrors": False,
    "no_warnings": True,
    "quiet": True,
    "noprogress": True,
    "color": {"stderr": "no_color", "stdout": "no_color"},
}

POST_METAPARSER = {
    "key": "MetadataParser",
    "when": "pre_process",
    "actions": [
        (
            MetadataParserPP.interpretter,
            "%(track,title)s",
            "%(title)s",
        ),
        (
            MetadataParserPP.interpretter,
            "%(artist,channel,creator,uploader|NA)s",
            "%(uploader)s",
        ),
        (
            MetadataParserPP.interpretter,
            "%(album_artist,uploader)s",
            "%(meta_album_artist)s",
        ),
        (
            MetadataParserPP.interpretter,
            "%(album,title)s",
            "%(meta_album)s",
        ),
        (
            MetadataParserPP.interpretter,
            "%(release_year,release_date>%Y,upload_date>%Y)s",
            "%(meta_date)s",
        ),
    ],
}

FORMAT_TYPE = Literal["video", "audio"]
MUSIC_SITES = frozenset({"music.youtube.com", "soundcloud.com", "bandcamp.com"})
InfoDict = NewType("InfoDict", dict[str, Any])

YTDLP = YoutubeDL(
    OPTS_BASE
    | {
        "skip_download": True,
        "extract_flat": "in_playlist",
        "postprocessors": [POST_METAPARSER],
    }
)
"""Base YT-DLP instance. Can extract info but not download."""


class SupportedExtensions(frozenset[str], Enum):
    """Sets of file extensions supported by YT-DLP."""

    video = frozenset(MEDIA_EXTENSIONS.video)
    audio = frozenset(MEDIA_EXTENSIONS.audio)


# Helpers
def run_postproces(file: Path, info: InfoDict, params: dict[str, Any]) -> Path:
    """Postprocess file by params."""

    with YoutubeDL(OPTS_BASE | params) as ydl:
        info = ydl.post_process(filename=str(file), info=info)

    return Path(info["filepath"])


def parse_name_template(info: InfoDict, template="%(uploader)s - %(title)s") -> str:
    """Get a custom filename by output template."""

    name = YTDLP.prepare_outtmpl(template, info)
    return cast(str, name)


def format_except_msg(exception: Exception) -> str:
    """Get a user friendly message of a YT-DLP message exception."""

    msg = str(exception)

    # No connection
    if "HTTP Error" in msg:
        pass

    elif "Read timed out" in msg:
        msg = "Download timeout."

    elif "[Errno -3]" in msg or "Failed to extract any player response" in msg:
        msg = "No internet connection."

    # Invalid URL
    elif (
        "Unable to download webpage" in msg
        and "[Errno -2]" in msg
        or "[Errno -5]" in msg
    ):
        msg = "Invalid URL."

    elif "is not a valid URL" in msg:
        splits = msg.split()
        msg = splits[1] + " is not a valid URL."

    elif "Unsupported URL" in msg:
        splits = msg.split()
        msg = "Unsupported URL: " + splits[3]

    # Postprocessing
    elif "Unable to rename file" in msg:
        msg = "Unable to rename file."

    elif "ffmpeg not found" in msg:
        msg = "Postprocessing failed. FFmpeg executable not founded."

    # General
    elif "Unable to download" in msg or "Got error" in msg:
        msg = "Unable to download."

    # Last parse
    if msg.startswith("ERROR: "):
        msg = msg.strip("ERROR: ")

    return msg


# Directories
DIR_TEMP = Path(mkdtemp(prefix="ydl-"))


def clean_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(DIR_TEMP)


atexit.register(clean_tempdir)
