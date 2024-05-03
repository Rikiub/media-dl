from __future__ import annotations

from dataclasses import dataclass

from media_dl.extractor import info_helper
from media_dl.models.base import ExtractID
from media_dl.models.stream import Stream, InfoDict


@dataclass(slots=True, frozen=True)
class Playlist(ExtractID):
    """Stream list with basic metadata. Access them with attribute `streams`."""

    thumbnail: str
    title: str
    streams: list[Stream]

    @classmethod
    def _from_info(cls, info: InfoDict) -> Playlist:
        if not info_helper.is_playlist(info):
            raise TypeError("Unable to serialize dict. Not is a playlist.")

        return cls(
            *info_helper.extract_meta(info),
            thumbnail=info_helper.extract_thumbnail(info),
            title=info.get("title") or "",
            streams=[Stream._from_info(entry) for entry in info["entries"]],
        )

    def __len__(self):
        return len(self.streams)
