from dataclasses import dataclass
from typing import Any, get_args
from pathlib import Path

from media_dl.types import ydl_opts
from media_dl.types.formats import FORMAT, EXTENSION, EXT_VIDEO, EXT_AUDIO


@dataclass(slots=True)
class DownloadConfig:
    format: FORMAT
    convert_to: EXTENSION | None = None
    video_quality: int = 1080
    audio_quality: int = 9
    embed_metadata: bool = True
    output: Path | str = Path.cwd()

    def __post_init__(self):
        self.output = Path(self.output)

        if not self.output.is_dir:
            raise ValueError(f"'{self.output}' not is a directory.")
        if self.convert_to:
            if not (
                self.format == "video"
                and self.convert_to in get_args(EXT_VIDEO)
                or self.format == "audio"
                and self.convert_to in get_args(EXT_AUDIO)
            ):
                raise ValueError(
                    f"The '{self.format}' format and the '{self.convert_to}' extension to be converted are incompatible."
                )

    def gen_opts(self) -> dict[str, Any]:
        opts = ydl_opts.BASE_OPTS | ydl_opts.DOWNLOAD_OPTS
        opts["paths"]["home"] = str(self.output)

        match self.format:
            case "video":
                resolution = str(self.video_quality)
                opts |= {
                    "format": f"bv[height<={resolution}]+ba/bv[height<={resolution}]/b",
                    "merge_output_format": "/".join(get_args(EXT_VIDEO)),
                    "subtitleslangs": "all",
                    "writesubtitles": True,
                }

                if self.convert_to:
                    opts |= {"final_ext": self.convert_to}
                    opts["postprocessors"].append(
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": self.convert_to,
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

                opts["postprocessors"].append(
                    {
                        "key": "FFmpegExtractAudio",
                        "nopostoverwrites": True,
                        "preferredcodec": (
                            self.convert_to
                            if self.convert_to in get_args(EXT_AUDIO)
                            else None
                        ),
                        "preferredquality": self.audio_quality,
                    }
                )

                if self.convert_to:
                    opts |= {"final_ext": self.convert_to}

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
                raise ValueError(f"'{self.format}' is invalid.")

        if self.embed_metadata:
            # Metadata Postprocessors
            opts["postprocessors"].append(
                {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True}
            )
            opts["postprocessors"].append(
                {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False}
            )
            opts["postprocessors"].append(
                {"key": "EmbedThumbnail", "already_have_thumbnail": False}
            )

        return opts
