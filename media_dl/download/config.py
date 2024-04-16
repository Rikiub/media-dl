from typing import Literal, Any, cast, get_args
from dataclasses import dataclass, asdict
from pathlib import Path
import shutil
from os import PathLike
import os

from yt_dlp import YoutubeDL

from media_dl.helper import OPTS_BASE, OPTS_METAPARSER, FORMAT_TYPE, InfoDict

StrPath = str | PathLike[str]

EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "ogg"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common lossy compression containers formats with thumbnail and metadata support."""

FILE_REQUEST = Literal[FORMAT_TYPE, EXTENSION]
VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080]


@dataclass(slots=True)
class FormatConfig:
    """Helper to create download params to `YT-DLP` and provide a simple interface for others downloaders.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: Target file format to search or convert if is a extension.
        quality: Target quality to try filter.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable. By default, it'll try get the global installed FFmpeg.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
        remux: If format extension not specified, will convert to most compatible extension when necessary. (FFmpeg)
    """

    format: FILE_REQUEST
    quality: int | None = None
    output: StrPath = Path.cwd()
    ffmpeg: StrPath | None = None
    metadata: bool = True
    remux: bool = True

    def __post_init__(self):
        self.output = Path(self.output)
        self.ffmpeg = Path(self.ffmpeg) if self.ffmpeg else None

        # Check if ffmpeg is installed and handle custom path.
        if p := self.ffmpeg:
            if not self._executable_exists(p):
                raise FileNotFoundError(f"'{p.name}' is not a FFmpeg executable.")
        else:
            self.ffmpeg = self._get_global_ffmpeg() or None

    @property
    def type(self) -> FORMAT_TYPE:
        """Config generic type."""

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
        """Check if config would convert the files.

        Returns:
            If could convert, will return a file extension string. Else return `None`.
        """

        return (
            cast(EXTENSION, self.format) if self.format in get_args(EXTENSION) else None
        )

    def asdict(self) -> dict[str, Any]:
        """Convert config to simple dict."""

        d = asdict(self)

        # Convert pathlib.Path to string
        for key, value in d.items():
            if isinstance(value, Path):
                d[key] = str(value)

        return d

    @staticmethod
    def _get_global_ffmpeg() -> Path | None:
        if path := shutil.which("ffmpeg"):
            return Path(path)
        else:
            return None

    @staticmethod
    def _executable_exists(file: StrPath) -> bool:
        file = Path(file)

        if file.is_file() and os.access(file, os.X_OK):
            return True
        else:
            return False

    def _run_postproces(self, file: StrPath, info: InfoDict) -> Path:
        with YoutubeDL(OPTS_BASE | self._gen_opts()) as ydl:
            info = ydl.post_process(filename=str(file), info=info)
            return Path(info["filepath"])

    def _gen_opts(self) -> dict[str, Any]:
        opts = {"overwrites": False, "retries": 3}

        post = OPTS_METAPARSER
        post["when"] = "post_process"
        postprocessors = [OPTS_METAPARSER]

        if self.ffmpeg:
            opts |= {"ffmpeg_location": str(self.ffmpeg)}

        if self.ffmpeg and self.remux:
            postprocessors.append(
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "opus>ogg/aac>m4a/alac>m4a/mov>mp4/webm>mkv",
                },
            )

        match self.type:
            case "video":
                opts |= {
                    "subtitleslangs": "all",
                    "writesubtitles": True,
                }

                if self.ffmpeg and self.convert:
                    opts |= {"final_ext": self.format}
                    postprocessors.append(
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": self.format,
                        }
                    )
            case "audio":
                opts |= {
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
                    postprocessors.append(
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
            postprocessors.extend(
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

        opts |= {"postprocessors": postprocessors}
        return opts
