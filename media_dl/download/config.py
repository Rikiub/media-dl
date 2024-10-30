from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast, get_args

from media_dl._ydl import POST_MUSIC
from media_dl.path import check_executable_exists, get_global_ffmpeg
from media_dl.types import EXT_AUDIO, EXT_VIDEO, EXTENSION, FILE_FORMAT, FORMAT_TYPE


@dataclass(slots=True)
class FormatConfig:
    """Configuration to shape the formats to download.

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
        if self.ffmpeg and not check_executable_exists(self.ffmpeg):
            raise FileNotFoundError(f"'{self.ffmpeg.name}' is not a FFmpeg executable.")
        else:
            self.ffmpeg = get_global_ffmpeg() or None

    @property
    def type(self) -> FORMAT_TYPE:
        """Determine general type.

        Returns:
            "video" or "audio".
        """

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
        """Check if would convert the files.

        Returns:
            If could convert, returns a file `EXTENSION`, else return `None`.
        """

        return (
            cast(EXTENSION, self.format) if self.format in get_args(EXTENSION) else None
        )

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict."""

        d = asdict(self)

        # Convert pathlib.Path to str
        for key, value in d.items():
            if isinstance(value, Path):
                d[key] = str(value)

        return d

    def ydl_params(
        self,
        overwrite: bool = False,
        music_meta: bool = False,
    ) -> dict[str, Any]:
        """Generate download parameters for YT-DLP."""

        params = {"overwrites": overwrite}
        if self.convert:
            params |= {"final_ext": self.format}

        postprocessors = []
        if music_meta:
            postprocessors.extend(POST_MUSIC)

        if self.ffmpeg:
            params |= {"ffmpeg_location": str(self.ffmpeg)}

            match self.type:
                case "video":
                    postprocessors.append(
                        {
                            "key": "FFmpegVideoRemuxer",
                            "preferedformat": self.convert or "webm>mkv",
                        },
                    )
                case "audio":
                    postprocessors.append(
                        {
                            "key": "FFmpegExtractAudio",
                            "nopostoverwrites": not overwrite,
                            "preferredcodec": self.convert,
                            "preferredquality": None,
                        }
                    )

                    # Square thumbnail
                    params |= {
                        "postprocessor_args": {
                            "thumbnailsconvertor+ffmpeg_o": [
                                "-c:v",
                                "png",
                                "-vf",
                                "crop=ih",
                            ]
                        },
                    }
                case _:
                    raise TypeError(f"Type '{self.format}' is not 'video' or 'audio'")

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
                        {"key": "EmbedThumbnail", "already_have_thumbnail": False},
                    ]
                )

        params |= {"postprocessors": postprocessors}
        return params
