from typing import Annotated
from pydantic import BaseModel, Field, OnErrorOmit


class MusicMetadata(BaseModel):
    track: str = ""
    artists: list[str] = []
    album: str = ""
    album_artist: str = ""
    genres: list[str] = []


class Subtitle(BaseModel):
    url: str
    extension: Annotated[str, Field(alias="ext")]
    language: Annotated[str, Field(alias="name")] = ""


class Thumbnail(BaseModel):
    id: str
    url: str
    width: int = 0
    height: int = 0


ThumbnailList = list[OnErrorOmit[Thumbnail]]
