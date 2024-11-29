from os import PathLike
from typing import Any, Literal

# FORMAT
VIDEO_EXTENSION = Literal["mp4", "mkv", "mov"]
AUDIO_EXTENSION = Literal["m4a", "opus", "mp3"]
EXTENSION = Literal[VIDEO_EXTENSION, AUDIO_EXTENSION]
"""Common lossy compression containers formats with thumbnail and metadata support."""

FORMAT_TYPE = Literal["video", "audio"]

FILE_FORMAT = Literal[FORMAT_TYPE, EXTENSION]
VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080]

# SEARCH
SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]
MUSIC_SITES = frozenset({"music.youtube.com", "soundcloud.com", "bandcamp.com"})

# Extra
InfoDict = dict[str, Any]
StrPath = str | PathLike[str]
