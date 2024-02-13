from typing import get_args, Literal
from enum import Enum

FORMAT = Literal["video", "audio"]
EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "ogg"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common containers formats with thumbnail, metadata and lossy compression support."""

AUDIO_QUALITY = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]

SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]


class FormatTuples(tuple, Enum):
    format = get_args(FORMAT)
    video_exts = get_args(EXT_VIDEO)
    audio_exts = get_args(EXT_AUDIO)
    video_res = get_args(VIDEO_RES)
    audio_quality = get_args(AUDIO_QUALITY)
