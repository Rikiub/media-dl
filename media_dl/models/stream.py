from __future__ import annotations

from dataclasses import dataclass, field

from media_dl.extractor import serializer
from media_dl.models.base import ExtractID, InfoDict
from media_dl.models.format import FormatList


@dataclass(slots=True, frozen=True)
class Stream(ExtractID):
    """Single `Stream` information.

    If `Stream` was obtained from a `Playlist`, will be incomplete and couldn't have `formats` to filter.
    To access to complete `Stream` information, you need do::

        >>> stream = stream.update()
    """

    _extra_info: InfoDict = field(repr=False)
    title: str
    uploader: str = ""
    thumbnail: str = ""
    duration: int = 0
    formats: FormatList = FormatList([])

    def update(self) -> Stream:
        """Get updated version of the `Stream` doing another request."""
        return self.from_url(self.url)

    @property
    def display_name(self) -> str:
        """Get pretty representation of the `Stream` name."""

        if self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return "?"

    def _is_music_site(self) -> bool:
        track = self._extra_info.get("track")
        artist = self._extra_info.get("artist")

        if track and artist or self.url in ("soundcloud.com"):
            return True
        else:
            return False

    @classmethod
    def _from_info(cls, info: InfoDict) -> Stream:
        if serializer.info_is_playlist(info):
            raise TypeError(
                "Unable to serialize dict. It's a playlist, not single stream."
            )

        return cls(
            *serializer.info_extract_meta(info),
            _extra_info=serializer.sanitize_info(info),
            title=info.get("title") or "",
            uploader=info.get("uploader") or "",
            thumbnail=serializer.info_extract_thumbnail(info),
            duration=info.get("duration") or 0,
            formats=FormatList._from_info(info),
        )
