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


# Directories
DIR_TEMP = Path(mkdtemp(prefix="ydl-"))


def clean_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(DIR_TEMP)


atexit.register(clean_tempdir)


# YTDLP Types
InfoDict = NewType("InfoDict", dict[str, Any])
FORMAT_TYPE = Literal["video", "audio"]
MUSIC_SITES = frozenset({"music.youtube.com", "soundcloud.com", "bandcamp.com"})

# YTDLP Base
_supress_logger = logging.getLogger("YoutubeDL")
_supress_logger.disabled = True

OPTS_BASE = {
    "logger": _supress_logger,
    "ignoreerrors": False,
    "no_warnings": True,
    "noprogress": True,
    "quiet": True,
    "color": {"stderr": "no_color", "stdout": "no_color"},
}

POST_MUSIC = {
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

YTDLP = YoutubeDL(
    OPTS_BASE
    | {
        "skip_download": True,
        "extract_flat": "in_playlist",
        "postprocessors": [POST_MUSIC],
    }
)
"""Base YT-DLP instance. Can extract info but not download."""


class SupportedExtensions(frozenset[str], Enum):
    """Sets of file extensions supported by YT-DLP."""

    video = frozenset(MEDIA_EXTENSIONS.video)
    audio = frozenset(MEDIA_EXTENSIONS.audio)
    thumbnail = frozenset(
        {"mp3", "mkv", "mka", "ogg", "opus", "flac", "m4a", "mp4", "m4v", "mov"}
    )


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


def download_thumbnail(filename: str, info: InfoDict) -> Path | None:
    with YoutubeDL(OPTS_BASE | {"writethumbnail": True}) as ydl:
        final = ydl._write_thumbnails(
            label=filename, info_dict=info, filename=str(DIR_TEMP / filename)
        )

    if final:
        return Path(final[0][0])
    else:
        return None


def download_subtitle(filename: str, info: InfoDict) -> Path | None:
    with YoutubeDL(OPTS_BASE | {"writesubtitles": True, "allsubtitles": True}) as ydl:
        subs = ydl.process_subtitles(
            "subtitle", info.get("subtitles"), info.get("automatic_captions")
        )
        info |= {"requested_subtitles": subs}

        final = ydl._write_subtitles(info_dict=info, filename=str(DIR_TEMP / filename))

    if final:
        return Path(final[0][0])
    else:
        return None


def format_except_msg(exception: Exception) -> str:
    """Get a user friendly message of a YT-DLP message exception."""

    msg = str(exception)

    # No connection
    if "HTTP Error" in msg:
        pass

    elif "Read timed out" in msg:
        msg = "Read timed out."

    elif any(msg in s for s in ("[Errno -3]", "Failed to extract any player response")):
        msg = "No internet connection."

    # Invalid URL
    elif "Unable to download webpage" in msg and any(
        msg in s for s in ("[Errno -2]", "[Errno -5]")
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
    elif any(msg in s for s in ("Unable to download", "Got error")):
        msg = "Unable to download."

    elif "is only available for registered users" in msg:
        msg = "Only available for registered users."

    # Last parse
    if msg.startswith("ERROR: "):
        msg = msg.strip("ERROR: ")

    return msg
