from typing import Literal

# FORMAT
EXT_VIDEO = Literal["mp4", "mkv", "mov"]
EXT_AUDIO = Literal["m4a", "opus", "mp3"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common lossy compression containers formats with thumbnail and metadata support."""

FORMAT_TYPE = Literal["video", "audio"]

FILE_FORMAT = Literal[FORMAT_TYPE, EXTENSION]
VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080]

# SEARCH
SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]
MUSIC_SITES = frozenset({"music.youtube.com", "soundcloud.com", "bandcamp.com"})
