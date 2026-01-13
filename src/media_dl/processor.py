from pathlib import Path
from typing import Literal

from media_dl.models.content.media import Media
from media_dl.models.format.types import Format
from media_dl.types import AUDIO_EXTENSION, EXTENSION, StrPath
from media_dl.ydl.processor import (
    RequestedFormat,
    RequestedFormats,
    YDLProcessor,
)
from media_dl.ydl.types import YDLExtractInfo

FormatPaths = list[tuple[Format, Path]]
ProcessorType = Literal[
    "change_container",
    "convert_audio",
    "merge_formats",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]


class MediaProcessor(YDLProcessor):
    def change_container(self, format: str | EXTENSION):
        return super().change_container(format)

    def convert_audio(
        self,
        format: str | AUDIO_EXTENSION = "",
        quality: int | None = None,
    ):
        return super().convert_audio(format, quality)

    def embed_metadata(
        self,
        data: YDLExtractInfo | Media,
        include_music: bool = False,
    ):
        if isinstance(data, Media):
            info = data.to_ydl_dict()
            if include_music:
                info |= _media_to_music_metadata(data)
        else:
            info = data

        super().embed_metadata(info)
        return self

    @classmethod
    def from_formats_merge(
        cls,
        filepath: StrPath,
        formats: RequestedFormats | FormatPaths,
        ffmpeg_path: StrPath | None = None,
    ):
        real_formats: list[RequestedFormat] = []

        for fmt in formats:
            if isinstance(fmt, tuple):
                format, path = fmt
                format: Format
                path: Path

                fmt = {"filepath": str(path)} | format.to_ydl_dict()
            real_formats.append(fmt)  # type: ignore

        cls = super().from_formats_merge(
            filepath,
            formats=real_formats,
            ffmpeg_path=ffmpeg_path,
        )
        return cls


def _media_to_music_metadata(media: Media) -> YDLExtractInfo:
    return {
        "meta_track": media.track or media.title,
        "meta_artist": ", ".join(media.artists) if media.artists else media.uploader,
        "meta_album_artist": media.album_artist or media.uploader,
        "meta_date": str(media.datetime.year) if media.datetime else "",
    }
