from dataclasses import dataclass
from pathlib import Path
from typing import Any

from media_dl.types.opts import EXTRACT_OPTS, DOWNLOAD_OPTS
from media_dl.types.formats import (
    FormatTuples,
    FORMAT,
    EXTENSION,
)


@dataclass(slots=True)
class DownloadConfig:
    format: FORMAT
    convert_to: EXTENSION | None = None
    video_res: int = 1080
    audio_quality: int = 9
    embed_metadata: bool = True
    output: Path | str = Path.cwd()

    def __post_init__(self):
        self.output = Path(self.output)

        if not self.output.is_dir:
            raise ValueError(f"'{self.output}' not is a directory.")
        if not self.audio_quality in FormatTuples.audio_quality:
            raise ValueError(
                f"'{self.audio_quality}' is out of range. Expected range between [1-9].",
            )
        if self.convert_to:
            if not (
                self.format == "video"
                and self.convert_to in FormatTuples.video_exts
                or self.format == "audio"
                and self.convert_to in FormatTuples.audio_exts
            ):
                raise ValueError(
                    f"The '{self.format}' format and the '{self.convert_to}' extension to be converted are incompatible."
                )

    def gen_opts(self) -> dict[str, Any]:
        opts = EXTRACT_OPTS | DOWNLOAD_OPTS
        opts["paths"]["home"] = str(self.output)

        match self.format:
            case "video":
                res = str(self.video_res if self.video_res else 4320)
                opts |= {
                    "format": f"bv[height<={res}]+ba/bv[height<={res}]/b",
                    "merge_output_format": "/".join(FormatTuples.video_exts),
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
                            if self.convert_to in FormatTuples.video_exts
                            else None
                        ),
                        "preferredquality": (
                            self.audio_quality if self.audio_quality != 9 else None
                        ),
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
                raise ValueError()

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
