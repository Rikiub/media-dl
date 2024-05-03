from typing import Literal, Any, cast, get_args
from dataclasses import dataclass, asdict
from pathlib import Path
import shutil
import os

from media_dl._ydl import FORMAT_TYPE


EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "opus"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common lossy compression containers formats with thumbnail and metadata support."""

FILE_FORMAT = Literal[FORMAT_TYPE, EXTENSION]
VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080]


@dataclass(slots=True)
class FormatConfig:
    """Helper to create download params to `YT-DLP` and provide a simple interface for others downloaders.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: Target file format to search or convert if is a extension.
        quality: Target quality to try filter.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
    """

    format: FILE_FORMAT
    quality: int | None = None
    output: Path = Path.cwd()
    ffmpeg: Path | None = None
    metadata: bool = True

    def __post_init__(self):
        # Check if ffmpeg is installed and handle custom path.
        if self.ffmpeg and not self._executable_exists(self.ffmpeg):
            raise FileNotFoundError(f"'{self.ffmpeg.name}' is not a FFmpeg executable.")
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
            raise TypeError(self.format, "is invalid. Should be:", FILE_FORMAT)

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

        # Convert pathlib.Path to str
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
    def _executable_exists(file: Path) -> bool:
        if file.is_file() and os.access(file, os.X_OK):
            return True
        else:
            return False

    def _gen_opts(self) -> dict[str, Any]:
        opts = {"overwrites": False, "retries": 3, "fragment_retries": 3}
        postprocessors: list[dict] = [
            {
                "key": "SponsorBlock",
                "when": "after_filter",
                "categories": {
                    "sponsor",
                    "selfpromo",
                    "intro",
                    "outro",
                    "music_offtopic",
                },
                "api": "https://sponsor.ajay.app",
            },
            {
                "key": "ModifyChapters",
                "force_keyframes": False,
                "remove_chapters_patterns": [],
                "remove_ranges": [],
                "remove_sponsor_segments": set(),
                "sponsorblock_chapter_title": "[SponsorBlock]: " "%(category_names)l",
            },
        ]

        if self.convert:
            opts |= {"final_ext": self.format}

        if self.ffmpeg:
            opts |= {"ffmpeg_location": str(self.ffmpeg)}

            if self.type == "video":
                if self.convert:
                    opts |= {"merge_output_format": self.convert}
                    postprocessors.append(
                        {
                            "key": "FFmpegVideoRemuxer",
                            "preferedformat": self.convert,
                        },
                    )
            elif self.type == "audio":
                postprocessors.append(
                    {
                        "key": "FFmpegExtractAudio",
                        "nopostoverwrites": True,
                        "preferredcodec": self.convert,
                        "preferredquality": None,
                    }
                )

                # Square thumbnail
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
            else:
                raise TypeError(f"Type '{self.format}' is not 'video' or 'audio'")

            if not self.convert:
                postprocessors.append(
                    {
                        "key": "FFmpegVideoRemuxer",
                        "preferedformat": "aac>m4a/alac>m4a/mov>mp4/webm>mkv",
                    },
                )

            if self.metadata:
                postprocessors.extend(
                    [
                        {
                            "key": "FFmpegMetadata",
                            "add_metadata": True,
                            "add_chapters": True,
                            "add_infojson": None,
                        },
                        {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False},
                    ]
                )

        postprocessors.append(
            {"key": "EmbedThumbnail", "already_have_thumbnail": False}
        )

        opts |= {"postprocessors": postprocessors}
        return opts
