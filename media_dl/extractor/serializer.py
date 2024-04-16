"""Helpers to serializer info dicts."""

from typing import cast

from media_dl.models import Playlist, Stream
from media_dl.helper import InfoDict, YTDLP


def info_to_dataclass(info: InfoDict) -> Stream | Playlist:
    """Serialize information from a info dict.

    Returns:
        - Single `Stream`.
        - `Playlist` with multiple `Streams`.

    Raises:
        TypeError: Not is a valid info dict.
    """

    if info_is_playlist(info):
        return Playlist._from_info(info)
    elif info_is_stream(info):
        return Stream._from_info(info)
    else:
        raise TypeError(info, "not is a valid info dict.")


def sanitize_info(info: InfoDict) -> InfoDict:
    """Remove unnecesary and risky information from info dict."""

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


def info_is_playlist(info: InfoDict) -> bool:
    """Check if info is a playlist."""
    return True if info.get("_type") == "playlist" or info.get("entries") else False


def info_is_stream(info: InfoDict) -> bool:
    """Check if info is a single Stream."""
    return True if info.get("formats") else False


def info_extract_thumbnail(info: InfoDict) -> str:
    """Extract thumbnail from a stream info dict."""
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
