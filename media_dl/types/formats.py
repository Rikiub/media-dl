from typing import Literal

SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]
VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]

FORMAT = Literal["video", "audio"]
EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "ogg"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common containers formats with thumbnail, metadata and lossy compression support."""
