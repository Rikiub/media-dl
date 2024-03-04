from typing import Literal, Any, cast, get_args
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import shutil
from os import PathLike
import os

from yt_dlp.utils import MEDIA_EXTENSIONS

from media_dl.dirs import DIR_TEMP
from media_dl.ydl_base import BASE_OPTS, DOWNLOAD_OPTS

StrPath = str | PathLike[str]


class SupportedExtensions(set[str], Enum):
    video = set(MEDIA_EXTENSIONS.video)
    audio = set(MEDIA_EXTENSIONS.audio)


VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080]

EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "ogg"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common lossy compression containers formats with thumbnail and metadata support."""

FORMAT_TYPE = Literal["video", "only-audio"]
FILE_REQUEST = Literal[FORMAT_TYPE, EXTENSION]


@dataclass(slots=True)
class FormatConfig:
    """Helper to create download params to yt-dlp.

    If ffmpeg if not installed, some options will not be available (metadata, remux).
    """

    format: FILE_REQUEST
    output: StrPath = Path.cwd()
    ffmpeg_path: StrPath = ""
    embed_metadata: bool = True
    remux: bool = True

    def __post_init__(self):
        # Check if has valid format.
        self.target_type

        # Check if ffmpeg is installed and handle custom path.
        if self.ffmpeg_path:
            path = Path(self.ffmpeg_path)

            if not self._valid_executable(path):
                raise FileNotFoundError(
                    f"'{path.name}' is not a executable file.",
                )
        else:
            self.ffmpeg_path = self._get_global_ffmpeg() or ""

        self.output = str(self.output)
        self.ffmpeg_path = str(self.ffmpeg_path)

    @property
    def target_type(self) -> FORMAT_TYPE:
        if self.format in get_args(FORMAT_TYPE):
            return cast(FORMAT_TYPE, self.format)

        elif self.format in get_args(EXT_VIDEO):
            return "video"

        elif self.format in get_args(EXT_AUDIO):
            return "only-audio"

        else:
            raise TypeError(
                self.format, "is invalid. Should be:", FORMAT_TYPE, EXTENSION
            )

    @property
    def target_convert(self) -> EXTENSION | None:
        """Check if can convert the file."""
        return (
            cast(EXTENSION, self.format) if self.format in get_args(EXTENSION) else None
        )

    def asdict(self) -> dict[str, Any]:
        return asdict(self)

    def is_ffmpeg_installed(self) -> bool:
        return self._valid_executable(self.ffmpeg_path)

    def gen_opts(self) -> dict[str, Any]:
        ffmpeg = self.is_ffmpeg_installed()

        opts = BASE_OPTS | DOWNLOAD_OPTS
        opts |= {
            "paths": {
                "home": str(self.output),
                "temp": str(DIR_TEMP),
            },
            "ffmpeg_location": str(self.ffmpeg_path) if ffmpeg else "",
        }

        if ffmpeg and self.remux:
            opts["postprocessors"].append(
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "opus>ogg/aac>m4a/alac>m4a/mov>mp4/webm>mkv",
                },
            )

        match self.target_type:
            case "video":
                opts |= {
                    "format": "bv+ba/" if ffmpeg else "" + "bv/b",
                    "merge_output_format": (
                        self.format
                        if self.target_convert
                        else "/".join(get_args(EXT_VIDEO))
                    ),
                    "subtitleslangs": "all",
                    "writesubtitles": True,
                }

                if ffmpeg and self.target_convert:
                    opts |= {"final_ext": self.format}
                    opts["postprocessors"].append(
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": self.format,
                        }
                    )
            case "only-audio":
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

                if ffmpeg:
                    opts["postprocessors"].append(
                        {
                            "key": "FFmpegExtractAudio",
                            "nopostoverwrites": True,
                            "preferredcodec": (
                                self.format if self.target_convert else None
                            ),
                            "preferredquality": None,
                        }
                    )

                if ffmpeg and self.target_convert:
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

        if ffmpeg and self.embed_metadata:
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

    def _valid_executable(self, file: StrPath) -> bool:
        path = Path(file)

        if path.exists() and os.access(path, os.X_OK):
            return True
        else:
            return False
