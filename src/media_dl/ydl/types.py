from enum import Enum
from typing import Any

from yt_dlp.utils import MEDIA_EXTENSIONS


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


YDLExtractInfo = dict[str, Any]
YDLParams = dict[str, Any]
