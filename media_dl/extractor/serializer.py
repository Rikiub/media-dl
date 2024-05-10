"""Helpers to serialize info dicts."""

from typing import cast

from media_dl._ydl import InfoDict, YTDLP


def is_playlist(info: InfoDict) -> bool:
    """Check if info is a playlist."""

    if info.get("_type") == "playlist" or info.get("entries"):
        return True
    else:
        return False


def is_stream(info: InfoDict) -> bool:
    """Check if info is a single Stream."""

    if info.get("_type") == "url" or info.get("formats"):
        return True
    else:
        return False


def sanitize(info: InfoDict) -> InfoDict:
    """Remove unnecesary and risky information from info dict."""

    info = cast(InfoDict, YTDLP.sanitize_info(info))

    keys_to_remove = {
        "requested_subtitles",
        "requested_formats",
        "formats",
        "_version",
    }

    for key in keys_to_remove:
        info.pop(key, None)

    return info


def extract_thumbnail(info: InfoDict) -> str:
    """Extract thumbnail from a stream info dict."""

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
