from pathlib import Path

from media_dl import _ydl as ydl
from media_dl.models.metadata import Thumbnail
from media_dl.types import StrPath


def download_thumbnails(filename: StrPath, thumbnails: list[Thumbnail]) -> Path | None:
    info = {"thumbnails": [t.model_dump() for t in thumbnails]}
    path = ydl.download_thumbnail(str(filename), info)
    return path


def download_subtitles(filename: StrPath, subtitles: dict):
    info = subtitles.get("subtitles")

    if info:
        info = subtitles["subtitles"]
    else:
        info = subtitles

    path = ydl.download_subtitle(str(filename), info)

    return path
