from pathlib import Path

from media_dl.models.metadata import Subtitles, Thumbnail
from media_dl.models.stream import Stream
from media_dl.types import StrPath
from media_dl.ydl.postprocessor import YDLPostProcessor
from media_dl.ydl.types import YDLExtractInfo


class PostProcessor(YDLPostProcessor):
    def embed_metadata(
        self,
        data: YDLExtractInfo | Stream,
        include_music: bool = False,
    ):
        if isinstance(data, Stream):
            info = data.to_ydl_dict()
            if include_music:
                info |= _stream_to_music_metadata(data)
        else:
            info = data

        super().embed_metadata(info)
        return self

    def embed_thumbnail(
        self,
        thumbnail: StrPath | Thumbnail,
        square: bool = False,
    ):
        if isinstance(thumbnail, Thumbnail):
            new_thumbnail = thumbnail.download(self.filepath)

            if not new_thumbnail:
                raise ValueError("Invalid thumbnail.")
        else:
            new_thumbnail = Path(thumbnail)

        super().embed_thumbnail(new_thumbnail, square)
        return self

    def embed_subtitles(
        self,
        subtitles: list[StrPath] | Subtitles,
    ):
        if isinstance(subtitles, Subtitles):
            new_subtitles = subtitles.download(self.filepath)

            if not new_subtitles:
                raise ValueError("Invalid subtitles.")
        else:
            new_subtitles = subtitles

        super().embed_subtitles(new_subtitles)  # type: ignore
        return self


def _stream_to_music_metadata(stream: Stream) -> YDLExtractInfo:
    return {
        "meta_track": stream.track or stream.title,
        "meta_artist": ", ".join(stream.artists) if stream.artists else stream.uploader,
        "meta_album_artist": stream.album_artist or stream.uploader,
        "meta_date": str(stream.datetime.year) if stream.datetime else "",
    }
