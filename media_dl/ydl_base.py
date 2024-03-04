"""Base yt-dlp parameters, functions and helpers used around the project."""

from typing import NewType, Any
import logging

from yt_dlp.postprocessor.metadataparser import MetadataParserPP

_supress_logger = logging.getLogger("YoutubeDL")
_supress_logger.disabled = True

InfoDict = NewType("InfoDict", dict[str, Any])


def is_playlist(info: InfoDict) -> bool:
    return True if info.get("_type") == "playlist" or info.get("entries") else False


def is_single(info: InfoDict) -> bool:
    return True if info.get("formats") else False


def better_exception_msg(msg: str, url: str) -> str:
    if "HTTP Error" in msg:
        pass

    elif "Unable to download" in msg or "Got error" in msg:
        msg = "Unable to download. Check your internet connection."

    elif "is not a valid URL" in msg:
        msg = url + " is not a valid URL"

    elif "Unsupported URL" in msg:
        msg = "Unsupported URL: " + url

    elif "ffmpeg not found" in msg:
        msg = "Postprocessing failed. FFmpeg executable not founded."

    if msg.startswith("ERROR: "):
        msg = msg.strip("ERROR: ")

    return msg


BASE_OPTS = {
    "ignoreerrors": False,
    "no_warnings": True,
    "noprogress": True,
    "quiet": True,
    "logger": _supress_logger,
    "color": {"stderr": "no_color", "stdout": "no_color"},
}
EXTRACT_OPTS = {"skip_download": True, "extract_flat": "in_playlist"}
DOWNLOAD_OPTS = {
    "outtmpl": {
        "default": "%(uploader)s - %(title)s.%(ext)s",
    },
    "overwrites": False,
    "retries": 3,
    "postprocessors": [
        {
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
                    "%(channel,uploader,creator,artist|null)s",
                    "%(uploader)s",
                ),
                (
                    MetadataParserPP.interpretter,
                    "%(album_artist,uploader)s",
                    "%(album_artist)s",
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
        },
    ],
}
