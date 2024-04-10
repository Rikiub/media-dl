"""Base yt-dlp parameters, functions and helpers used around the project."""

from typing import NewType, Any, cast
from tempfile import mkdtemp
from pathlib import Path
import logging
import atexit
import shutil

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.metadataparser import MetadataParserPP

# Directories
APPNAME = "media-dl"
DIR_TEMP = Path(mkdtemp(prefix="ydl-"))


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

OPTS_METAPARSER = {
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

InfoDict = NewType("InfoDict", dict[str, Any])
YTDLP = YoutubeDL(
    OPTS_BASE
    | {
        "skip_download": True,
        "extract_flat": "in_playlist",
        "postprocessors": [OPTS_METAPARSER],
    }
)


# Helper functions
def sanitize_info(info: InfoDict) -> InfoDict:
    info = cast(InfoDict, YTDLP.sanitize_info(info))

    keys_to_remove = {
        "requested_subtitles",
        "requested_formats",
        "formats",
        "heatmap",
        "_type",
        "_version",
    }

    for key in keys_to_remove:
        info.pop(key, None)

    return info


def parse_name_template(info: InfoDict, template="%(uploader)s - %(title)s") -> str:
    name = YTDLP.prepare_outtmpl(template, info)
    return cast(str, name)


def info_is_playlist(info: InfoDict) -> bool:
    return True if info.get("_type") == "playlist" or info.get("entries") else False


def info_is_single(info: InfoDict) -> bool:
    return True if info.get("formats") else False


def info_extract_thumbnail(info: InfoDict) -> str:
    if t := info.get("thumbnail"):
        return t
    elif t := info.get("thumbnails"):
        return t[-1]["url"]
    else:
        return ""


def info_extract_meta(info: InfoDict) -> tuple[str, str, str]:
    """Helper for extract essential information from info dict.

    Returns:
        Tuple with 'extractor', 'id', 'url'.
    """

    try:
        extractor = info.get("extractor_key") or info["ie_key"]
        id = info["id"]
        url = info.get("original_url") or info["url"]
    except KeyError:
        raise TypeError(
            "Info dict should have the required keys: 'extractor_key', 'id', 'url'."
        )

    return extractor, id, url


def better_exception_msg(msg: str) -> str:
    if "HTTP Error" in msg:
        pass

    elif "Read timed out" in msg:
        msg = "Download timeout."

    # General error
    elif "Unable to download" in msg or "Got error" in msg:
        msg = "Unable to download."

    elif "[Errno -3]" in msg:
        msg = "Unable to establish internet connection."

    # Incomplete URL
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

    elif "Unable to rename file" in msg:
        msg = "Unable to rename file."

    elif "ffmpeg not found" in msg:
        msg = "Postprocessing failed. FFmpeg executable not founded."

    if msg.startswith("ERROR: "):
        msg = msg.strip("ERROR: ")

    return msg


# Cleaner
def clean_tempdir():
    shutil.rmtree(DIR_TEMP)


atexit.register(clean_tempdir)
