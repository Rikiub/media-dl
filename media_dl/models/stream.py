from __future__ import annotations

from dataclasses import dataclass

from media_dl import helper
from media_dl.models.base import (
    GLOBAL_INFO,
    ExtractID,
    InfoDict,
)
from media_dl.models.format import FormatList


@dataclass(slots=True, frozen=True)
class Stream(ExtractID):
    title: str
    uploader: str = ""
    thumbnail: str = ""
    duration: int = 0
    formats: FormatList = FormatList([])

    def update(self) -> Stream:
        """Get a update version of the Stream."""
        return self.from_url(self.url)

    @property
    def display_name(self) -> str:
        if self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return "?"

    @classmethod
    def _from_info(cls, info: InfoDict) -> Stream:
        if helper.is_playlist(info):
            raise TypeError(
                "Unable to serialize dict. It is a playlist, not a single stream."
            )
        elif helper.is_single(info):
            GLOBAL_INFO.save(info)

        return cls(
            *helper.extract_meta(info),
            thumbnail=helper.extract_thumbnail(info),
            title=info.get("track") or info.get("title") or "",
            uploader=(
                info.get("artist")
                or info.get("channel")
                or info.get("creator")
                or info.get("uploader")
                or ""
            ),
            duration=info.get("duration") or 0,
            formats=FormatList._from_info(info),
        )
