from typing import Annotated
from pydantic import BaseModel, Field


class MusicMetadata(BaseModel):
    track: str = ""
    artists: list[str] | None = None
    album: str = ""
    album_artist: str = ""
    genres: list[str] | None = None


class Subtitle(BaseModel):
    url: str
    extension: Annotated[str, Field(alias="ext")]
    language: Annotated[str, Field(alias="name")] = ""


Subtitles = dict[str, list[Subtitle]]


class Thumbnail(BaseModel):
    id: str
    url: str
    width: int = 0
    height: int = 0
