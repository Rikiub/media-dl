from pathlib import Path

from media_dl.models.metadata import Subtitle, Thumbnail
from media_dl.types import StrPath
from media_dl.ydl import helpers


def download_thumbnails(filename: StrPath, thumbnails: list[Thumbnail]) -> Path | None:
    info = {"thumbnails": [t.model_dump() for t in thumbnails]}
    path = helpers.download_thumbnail(str(filename), info)
    return path


def download_subtitles(filename: StrPath, subtitles: list[Subtitle]):
    info = {"subtitles": [s.model_dump() for s in subtitles]}
    path = helpers.download_subtitle(str(filename), info)
    return path
