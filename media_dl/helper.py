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


def extract_thumbnail(info: InfoDict) -> str:
    if t := info.get("thumbnail"):
        return t
    elif t := info.get("thumbnails"):
        return t[-1]["url"]
    else:
        return ""


def extract_meta(info: InfoDict) -> tuple[str, str, str]:
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


MUSIC_SITES = {
    "soundcloud.com",
    "music.youtube.com",
    "bandcamp.com",
}


BASE_OPTS = {
    "ignoreerrors": False,
    "no_warnings": True,
    "noprogress": True,
    "quiet": True,
    "logger": _supress_logger,
    "color": {"stderr": "no_color", "stdout": "no_color"},
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
                    "%(artist,channel,creator,uploader|NA)s",
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
