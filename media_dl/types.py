from typing import Literal, Generator
from dataclasses import dataclass

MEDIA_TYPE = Literal["video/audio", "only_audio"]


@dataclass(slots=True)
class Result:
    type: MEDIA_TYPE
    source: str
    id: str
    title: str
    uploader: str
    duration: int
    url: str
    thumbnail_url: str | None = None
    _formats: list[dict] | None = None

    @property
    def formats(self) -> dict | None:
        if self._formats:
            return {"title": self.title, "id": self.id, "formats": self._formats}
        else:
            return None


@dataclass(slots=True)
class Playlist:
    title: str
    entries: list[Result]

    def __iter__(self) -> Generator[Result, None, None]:
        for item in self.entries:
            yield item
