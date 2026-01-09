from pathlib import Path

from media_dl.models.metadata import Subtitles, Thumbnail
from media_dl.types import StrPath
from media_dl.ydl import helpers


def download_thumbnails(filename: StrPath, thumbnails: list[Thumbnail]) -> Path | None:
    info = {"thumbnails": [t.to_ydl_dict() for t in thumbnails]}
    path = helpers.download_thumbnail(str(filename), info)
    return path


def download_subtitles(filename: StrPath, subtitles: Subtitles) -> Path | None:
    info = {"subtitles": subtitles.to_ydl_dict()}
    path = helpers.download_subtitle(str(filename), info)
    return path
