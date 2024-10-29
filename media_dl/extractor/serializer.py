"""Helpers to serialize info dicts."""

from media_dl._ydl import InfoDict, sanitize_info


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

    info = sanitize_info(info)

    keys_to_remove = {
        "requested_subtitles",
        "requested_formats",
        "formats",
        "_version",
    }

    for key in keys_to_remove:
        info.pop(key, None)

    return info
