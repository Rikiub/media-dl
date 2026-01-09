from typing import Annotated

from pydantic import BeforeValidator, Field, RootModel

from media_dl.models.base import Serializable


def _validate_artists(value: list[str]) -> list[str]:
    if value and len(value) == 1:
        if artists := value[0].split(","):
            return artists
    return value


class MusicMetadata(Serializable):
    track: str = ""
    artists: Annotated[list[str] | None, BeforeValidator(_validate_artists)] = None
    album: str = ""
    album_artist: str = ""
    genres: list[str] | None = None


class Subtitle(Serializable):
    url: str
    extension: Annotated[str, Field(alias="ext")]
    language: Annotated[str, Field(alias="name")] = ""


class Subtitles(Serializable, RootModel[dict[str, list[Subtitle]]]): ...


class Thumbnail(Serializable):
    id: str = ""
    url: str
    width: int = 0
    height: int = 0


class Chapter(Serializable):
    start_time: int
    end_time: int
    title: str
