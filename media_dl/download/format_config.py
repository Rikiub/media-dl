from typing import Literal, Any, cast, get_args
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import shutil
from os import PathLike
import os

from yt_dlp.utils import MEDIA_EXTENSIONS

from media_dl.dirs import DIR_TEMP
from media_dl.models.format import FORMAT_TYPE
from media_dl.helper import BASE_OPTS

StrPath = str | PathLike[str]


class SupportedExtensions(set[str], Enum):
    video = set(MEDIA_EXTENSIONS.video)
    audio = set(MEDIA_EXTENSIONS.audio)


VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080]

EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "ogg"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common lossy compression containers formats with thumbnail and metadata support."""

FILE_REQUEST = Literal[FORMAT_TYPE, EXTENSION]


@dataclass(slots=True)
class FormatConfig:
    """Helper to create download params to yt-dlp.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: Target file format to search or convert if is a extension.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
        remux: If format extension not specified, will convert to most compatible extension when necessary. (FFmpeg)
    """

    format: FILE_REQUEST
    output: StrPath = Path.cwd()
    ffmpeg: StrPath | None = None
    metadata: bool = True
    remux: bool = True

    def __post_init__(self):
        # Check if ffmpeg is installed and handle custom path.
        if self.ffmpeg:
            path = Path(self.ffmpeg)

            if not self._executable_exists(path):
                raise FileNotFoundError(
                    f"'{path.name}' is not a FFmpeg executable.",
                )
        else:
            self.ffmpeg = self._get_global_ffmpeg() or None

        self.output = str(self.output)
        self.ffmpeg = str(self.ffmpeg)

    @property
    def type(self) -> FORMAT_TYPE:
        if self.format in get_args(FORMAT_TYPE):
            return cast(FORMAT_TYPE, self.format)

        elif self.format in get_args(EXT_VIDEO):
            return "video"
        elif self.format in get_args(EXT_AUDIO):
            return "audio"

        else:
            raise TypeError(self.format, "is invalid. Should be:", FILE_REQUEST)

    @property
    def convert(self) -> EXTENSION | None:
        """Check if can convert the file."""
        return (
            cast(EXTENSION, self.format) if self.format in get_args(EXTENSION) else None
        )

    def asdict(self) -> dict[str, Any]:
        return asdict(self)

    def _gen_opts(self) -> dict[str, Any]:
        opts = BASE_OPTS | {
            "outtmpl": "%(uploader,extractor)s - %(title,id)s.%(ext)s",
            "overwrites": False,
            "retries": 3,
        }
        opts |= {
            "paths": {
                "home": str(self.output),
                "temp": str(DIR_TEMP),
            },
            "ffmpeg_location": str(self.ffmpeg) if self.ffmpeg else None,
        }

        if self.ffmpeg and self.remux:
            opts["postprocessors"].append(
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "opus>ogg/aac>m4a/alac>m4a/mov>mp4/webm>mkv",
                },
            )

        match self.type:
            case "video":
                opts |= {
                    "format": "bv+ba/" if self.ffmpeg else "" + "bv/b",
                    "merge_output_format": (
                        self.format if self.convert else "/".join(get_args(EXT_VIDEO))
                    ),
                    "subtitleslangs": "all",
                    "writesubtitles": True,
                }

                if self.ffmpeg and self.convert:
                    opts |= {"final_ext": self.format}
                    opts["postprocessors"].append(
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": self.format,
                        }
                    )
            case "audio":
                opts |= {
                    "format": "ba/b",
                    "postprocessor_args": {
                        "thumbnailsconvertor+ffmpeg_o": [
                            "-c:v",
                            "png",
                            "-vf",
                            "crop=ih",
                        ]
                    },
                }

                if self.ffmpeg:
                    opts["postprocessors"].append(
                        {
                            "key": "FFmpegExtractAudio",
                            "nopostoverwrites": True,
                            "preferredcodec": self.format if self.convert else None,
                            "preferredquality": None,
                        }
                    )

                if self.ffmpeg and self.convert:
                    opts |= {"final_ext": self.format}

                    """
                    # Audio Lyrics support. Would be a new feature, see:
                    # https://github.com/yt-dlp/yt-dlp/pull/8869
                    opts["postprocessors"].append(
                        {
                            "key": "FFmpegSubtitlesConvertor",
                            "format": "lrc",
                            "when": "before_dl",
                        }
                    )
                    """
            case _:
                raise TypeError(self.format, "missmatch.")

        if self.ffmpeg and self.metadata:
            # Metadata Postprocessors
            opts["postprocessors"].extend(
                [
                    {
                        "key": "FFmpegMetadata",
                        "add_metadata": True,
                        "add_chapters": True,
                        "add_infojson": None,
                    },
                    {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False},
                    {"key": "EmbedThumbnail", "already_have_thumbnail": False},
                ]
            )

        return opts

    def _get_global_ffmpeg(self) -> str | None:
        if final_path := shutil.which("ffmpeg"):
            return str(final_path)
        else:
            return None

    def _executable_exists(self, file: StrPath) -> bool:
        path = Path(file)

        if path.exists() and os.access(path, os.X_OK):
            return True
        else:
            return False
