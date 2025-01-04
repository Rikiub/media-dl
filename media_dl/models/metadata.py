from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, computed_field


def _validate_artists(value: list[str]) -> list[str]:
    if value and len(value) == 1:
        if artists := value[0].split(","):
            return artists
    return value


class MusicMetadata(BaseModel):
    track: str = ""
    artists: Annotated[list[str] | None, BeforeValidator(_validate_artists)] = None
    album: str = ""
    album_artist: str = ""
    genres: list[str] | None = None

    @computed_field
    @property
    def artist(self) -> str:
        if self.artists:
            return self.artists[0]
        return ""


class Subtitle(BaseModel):
    url: str
    extension: Annotated[str, Field(alias="ext")]
    language: Annotated[str, Field(alias="name")] = ""


Subtitles = dict[str, list[Subtitle]]


class Thumbnail(BaseModel):
    id: str = ""
    url: str
    width: int = 0
    height: int = 0


class Chapter(BaseModel):
    start_time: int
    end_time: int
    title: str
