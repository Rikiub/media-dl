from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field, RootModel

from media_dl.models.content.base import YDLSerializable
from media_dl.types import StrPath


def _validate_artists(value: list[str]) -> list[str]:
    if value and len(value) == 1:
        if artists := value[0].split(","):
            return artists
    return value


class MusicMetadata(YDLSerializable):
    track: str = ""
    artists: Annotated[list[str] | None, BeforeValidator(_validate_artists)] = None
    album: str = ""
    album_artist: str = ""
    genres: list[str] | None = None


class Chapter(YDLSerializable):
    start_time: int
    end_time: int
    title: str


class Subtitle(YDLSerializable):
    url: str
    extension: Annotated[str, Field(alias="ext")]
    language: Annotated[str, Field(alias="name")] = ""


class Thumbnail(YDLSerializable):
    id: str = ""
    url: str
    width: int = 0
    height: int = 0

    def download(self, filepath: StrPath) -> Path:
        from media_dl.ydl.downloader import download_thumbnail

        info = {"thumbnails": [self.to_ydl_dict()]}
        path = download_thumbnail(filepath, info)
        return path


class Subtitles(YDLSerializable, RootModel[dict[str, list[Subtitle]]]):
    def download(self, filepath: StrPath) -> list[Path]:
        from media_dl.ydl.downloader import download_subtitles

        info = {"subtitles": self.to_ydl_dict()}
        paths = download_subtitles(filepath, info)
        return paths

    def __getitem__(self, index: int | str) -> list[Subtitle]:
        match index:
            case int():
                return list(self.root.values())[index]  # type: ignore
            case str():
                return self.root[index]
            case _:
                raise TypeError(index)

    def __bool__(self) -> bool:
        return bool(self.root)
