from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Any, overload

from media_dl._ydl import FORMAT_TYPE, InfoDict, SupportedExtensions
from media_dl.models.base import GenericList


@dataclass(slots=True, frozen=True, order=True)
class Format:
    """Remote file representation.

    Their fields are determined by their `type`. For example:
    - If is `video`, `extension` and `codec` would be mp4 and vp9.
    - If is `audio`, `extension` and `codec` would be m4a and opus.
    """

    url: str
    id: str
    type: FORMAT_TYPE
    extension: str
    codec: str
    quality: int = 0
    filesize: int = 0
    _downloader_options: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if not self.codec:
            raise TypeError("Must have a codec.")

        if not (
            self.extension in SupportedExtensions.video
            or self.extension in SupportedExtensions.audio
        ):
            raise TypeError(self.extension, "not is a valid extension.")

    @property
    def display_quality(self) -> str:
        """Get pretty representation of `Format` quality."""

        if self.type == "video":
            return str(self.quality) + "p"
        elif self.type == "audio":
            return str(round(self.quality)) + "kbps"
        else:
            return ""

    def _format_dict(self) -> InfoDict:
        d = {
            "format_id": self.id,
            "url": self.url,
            "ext": self.extension,
            "downloader_options": self._downloader_options,
        }

        match self.type:
            case "video":
                d |= {"height": self.quality, "vcodec": self.codec}
            case "audio":
                d |= {"abr": self.quality, "acodec": self.codec}
            case _:
                raise TypeError(self.type)

        if self.filesize != 0:
            d |= {"filesize": self.filesize}

        return InfoDict(d)

    @classmethod
    def _from_info(cls, entry: dict[str, Any]) -> Format:
        type: FORMAT_TYPE = (
            "audio" if entry.get("resolution", "") == "audio only" else "video"
        )

        match type:
            case "video":
                quality = entry.get("height")
                codec = entry.get("vcodec")
            case "audio":
                quality = entry.get("abr")
                codec = entry.get("acodec")
            case _:
                raise TypeError(type)

        cls = cls(
            url=entry["url"],
            id=entry["format_id"],
            type=type,
            extension=entry["ext"],
            codec=codec or "",
            quality=quality or 0,
            filesize=entry.get("filesize") or 0,
            _downloader_options=entry.get("downloader_options") or {},
        )
        cls.__post_init__()
        return cls


class FormatList(GenericList):
    """List of formats which can be filtered."""

    def type(self) -> FORMAT_TYPE:
        """
        Determine main format type.
        It will check if is 'video' or 'audio'.
        """

        if self.filter(type="video"):
            return "video"
        elif self.filter(type="audio"):
            return "audio"
        else:
            return "video"

    def filter(
        self,
        type: FORMAT_TYPE | None = None,
        extension: str | None = None,
        codec: str | None = None,
        quality: int | None = None,
    ) -> FormatList:
        """Get filtered format list by options."""

        formats = self._list

        if type:
            formats = [f for f in formats if f.type == type]
        if extension:
            formats = [f for f in formats if f.extension == extension]
        if quality:
            formats = [f for f in formats if f.quality == quality]
        if codec:
            formats = [f for f in formats if f.codec and f.codec.startswith(codec)]

        return FormatList(formats)

    def sort_by(self, attribute: str, reverse: bool = False) -> FormatList:
        """Sort by `Format` attribute."""

        return FormatList(
            sorted(self._list, key=lambda f: getattr(f, attribute), reverse=reverse)
        )

    def get_by_id(self, id: str) -> Format:
        """Get `Format` by `id`.

        Raises:
            IndexError: Provided id has not been founded.
        """

        if result := [f for f in self if f.id == id]:
            return result[0]
        else:
            raise IndexError(f"Format with id '{id}' has not been founded")

    def get_best_quality(self) -> Format:
        """Get `Format` with best quality."""

        formats = self.sort_by("quality")
        return formats[-1]

    def get_worst_quality(self) -> Format:
        """Get `Format` with worst quality."""

        formats = self.sort_by("quality")
        return formats[0]

    def get_closest_quality(self, quality: int) -> Format:
        """Get `Format` with closest quality."""

        qualities = [i.quality for i in self.sort_by("quality")]
        pos = bisect.bisect_left(qualities, quality)

        if pos == 0:
            return self[0]
        elif pos == len(self):
            return self[-1]
        else:
            before = self[pos - 1]
            after = self[pos]

            if after.quality - quality < quality - before.quality:
                return after
            else:
                return before

    @classmethod
    def _from_info(cls, info: InfoDict) -> FormatList:
        formats = []

        for format in info.get("formats") or {}:
            try:
                formats.append(Format._from_info(format))
            except TypeError:
                continue

        return FormatList(formats)

    def __contains__(self, other) -> bool:
        if isinstance(other, Format):
            try:
                self.get_by_id(other.id)
                return True
            except IndexError:
                return False
        else:
            return False

    @overload
    def __getitem__(self, index: int) -> Format: ...

    @overload
    def __getitem__(self, index: slice) -> FormatList: ...

    def __getitem__(self, index):
        match index:
            case int():
                return self._list[index]
            case slice():
                return FormatList(self._list[index])
            case _:
                raise TypeError(index)
