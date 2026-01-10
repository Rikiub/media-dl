from pathlib import Path

from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP
from yt_dlp.postprocessor.ffmpeg import (
    FFmpegEmbedSubtitlePP,
    FFmpegExtractAudioPP,
    FFmpegMetadataPP,
    FFmpegVideoRemuxerPP,
)
from yt_dlp.postprocessor.metadataparser import MetadataParserPP

from media_dl.types import StrPath
from media_dl.ydl.types import YDLExtractInfo


class YDLPostProcessor:
    def __init__(self, filepath: StrPath, ffmpeg_path: StrPath | None = None) -> None:
        self.filepath = Path(filepath)
        self.ffmpeg_path = ffmpeg_path

    @property
    def extension(self) -> str:
        return self.filepath.suffix[1:]

    def remux(self, format: str):
        pp = FFmpegVideoRemuxerPP(
            None,
            preferedformat=format,
        )
        _, data = pp.run(self.params)
        self.filepath = self._get_file(data)
        return self

    def extract_audio(
        self,
        codec: str = "",
        quality: int | None = None,
    ):
        pp = FFmpegExtractAudioPP(
            None,
            nopostoverwrites=False,
            preferredcodec=codec,
            preferredquality=quality,
        )

        _, data = pp.run(self.params)
        self.filepath = self._get_file(data)
        return

    def embed_metadata(self, data: YDLExtractInfo, include_music: bool = False):
        pp = FFmpegMetadataPP(
            None,
            add_metadata=True,
            add_chapters=True,
        )
        pp.run(self.params | data)

        if include_music:
            pp = MetadataParserPP(
                None,
                [
                    (
                        MetadataParserPP.interpretter,
                        "%(track,title)s",
                        "%(meta_track)s",
                    ),
                    (
                        MetadataParserPP.interpretter,
                        "%(artist,uploader)s",
                        "%(meta_artist)s",
                    ),
                    (
                        MetadataParserPP.interpretter,
                        "%(album,title)s",
                        "%(meta_album)s",
                    ),
                    (
                        MetadataParserPP.interpretter,
                        "%(album_artist,uploader)s",
                        "%(meta_album_artist)s",
                    ),
                    (
                        MetadataParserPP.interpretter,
                        "%(release_year,release_date>%Y,upload_date>%Y)s",
                        "%(meta_date)s",
                    ),
                ],
            )
            pp.run(self.params | data)

        return self

    def embed_thumbnail(self, thumbnail: StrPath, square: bool = False):
        pp = EmbedThumbnailPP()

        info = self.params | {
            "thumbnails": [
                {"filepath": str(thumbnail)},
            ],
        }

        if square:
            info |= {
                "postprocessor_args": {
                    "thumbnailsconvertor+ffmpeg_o": [
                        "-c:v",
                        "png",
                        "-vf",
                        "crop=ih",
                    ]
                }
            }

        pp.run(info)
        return self

    def embed_subtitles(self, subtitles: list[StrPath]):
        pp = FFmpegEmbedSubtitlePP()

        dict_subs: dict[str, dict] = {}
        for sub in subtitles:
            path = Path(sub)

            lang = path.suffixes[0][1:]
            ext = path.suffixes[1][1:]

            dict_subs |= {
                lang: {
                    "filepath": str(path),
                    "ext": str(ext),
                },
            }

        pp.run(self.params | {"requested_subtitles": dict_subs})
        return self

    @property
    def params(self):
        info = {
            "filepath": str(self.filepath),
            "ext": self.extension,
        }

        if self.ffmpeg_path:
            info |= {"ffmpeg_location": str(self.ffmpeg_path)}

        return info

    def _get_file(self, data: YDLExtractInfo) -> Path:
        return Path(data["filepath"])
