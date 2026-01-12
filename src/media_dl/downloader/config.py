from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast, get_args

from media_dl.path import get_ffmpeg
from media_dl.types import (
    AUDIO_EXTENSION,
    EXTENSION,
    FILE_FORMAT,
    FORMAT_TYPE,
    VIDEO_EXTENSION,
)


@dataclass(slots=True)
class FormatConfig:
    """Configuration to shape the formats to download.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: Target file format to search or convert if is a extension.
        quality: Target quality to try filter.
        output: Directory where to save files.
        ffmpeg_path: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
    """

    format: FILE_FORMAT
    quality: int | None = None
    output: Path = Path.cwd()
    ffmpeg_path: Path | None = None
    embed_metadata: bool = True

    def __post_init__(self):
        self.ffmpeg_path = get_ffmpeg(self.ffmpeg_path)

    @property
    def type(self) -> FORMAT_TYPE:
        """Determine general type.

        Returns:
            "video" or "audio".
        """

        if self.format in get_args(FORMAT_TYPE):
            return cast(FORMAT_TYPE, self.format)

        elif self.format in get_args(VIDEO_EXTENSION):
            return "video"

        elif self.format in get_args(AUDIO_EXTENSION):
            return "audio"

        else:
            raise TypeError(self.format, "is invalid. Should be:", FILE_FORMAT)

    @property
    def convert(self) -> EXTENSION | None:
        """Check if would convert the files.

        Returns:
            If could convert, returns a file `EXTENSION`, else return `None`.
        """

        return (
            cast(EXTENSION, self.format) if self.format in get_args(EXTENSION) else None
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""

        return asdict(self)
