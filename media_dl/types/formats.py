from typing import Literal, Any, get_args
from dataclasses import dataclass
from pathlib import Path

from media_dl.types import ydl_opts

SEARCH_PROVIDER = Literal["youtube", "ytmusic", "soundcloud"]
VIDEO_RES = Literal[144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]

FORMAT = Literal["best-video", "best-audio"]
EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "ogg"]
EXTENSION = Literal[EXT_VIDEO, EXT_AUDIO]
"""Common containers formats with thumbnail, metadata and lossy compression support."""


@dataclass(slots=True)
class FormatConfig:
    format: Literal[FORMAT, EXTENSION]
    video_quality: int = 1080
    audio_quality: int = 9
    embed_metadata: bool = True
    output: Path | str = Path.cwd()

    def __post_init__(self):
        output = Path(self.output)

        if not output.is_dir:
            raise ValueError(f"'{output}' not is a directory.")

    def gen_opts(self) -> dict[str, Any]:
        opts = ydl_opts.BASE_OPTS | ydl_opts.DOWNLOAD_OPTS
        opts["paths"]["home"] = str(self.output)

        convert = True if self.format in get_args(EXTENSION) else False

        if self.format in "best-video" or self.format in get_args(EXT_VIDEO):
            resolution = str(self.video_quality)
            opts |= {
                "format": f"bv[height<={resolution}]+ba/bv[height<={resolution}]/b",
                "merge_output_format": "/".join(get_args(EXT_VIDEO)),
                "subtitleslangs": "all",
                "writesubtitles": True,
            }

            if convert:
                opts |= {"final_ext": self.format}
                opts["postprocessors"].append(
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": self.format,
                    }
                )
        elif self.format in "best-audio" or self.format in get_args(EXT_AUDIO):
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

            opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "nopostoverwrites": True,
                    "preferredcodec": self.format if convert else None,
                    "preferredquality": self.audio_quality,
                }
            )

            if convert:
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
        else:
            raise ValueError(f"'{self.format}' is invalid.")

        if self.embed_metadata:
            # Metadata Postprocessors
            opts["postprocessors"].extend(
                [
                    {
                        "key": "FFmpegMetadata",
                        "add_metadata": True,
                        "add_chapters": True,
                    },
                    {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False},
                    {"key": "EmbedThumbnail", "already_have_thumbnail": False},
                ]
            )

        return opts
