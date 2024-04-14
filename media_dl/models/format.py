from __future__ import annotations

from typing import Literal, Any, overload
from dataclasses import dataclass, field
from collections.abc import Sequence
import bisect

from media_dl.models.base import InfoDict

FORMAT_TYPE = Literal["video", "audio"]


@dataclass(slots=True, frozen=True, order=True)
class Format:
    """Remote file representation.

    Their fields are determined by their `type`. For example:
    - If is `video`, `extension` and `codec` would be mp4 and vp9.
    - If is `audio`, `extension` and `codec` would be m4a and opus.
    """

    url: str
    id: str = field(hash=True, compare=True)
    type: FORMAT_TYPE
    extension: str
    quality: int = 0
    codec: str | None = None
    filesize: int | None = None
    _downloader_options: dict = field(default_factory=dict, repr=False)

    @property
    def display_quality(self) -> str:
        """Get pretty representation of `Format` quality."""

        if self.type == "video":
            return str(self.quality) + "p"
        elif self.type == "audio":
            return str(round(self.quality)) + "kbps"
        else:
            return "?"

    def _simple_format_dict(self) -> InfoDict:
        d = {
            "extractor": "generic",
            "extractor_key": "Generic",
            "id": self.id,
            "format_id": self.id,
            "url": self.url,
            "ext": self.extension,
            "downloader_options": self._downloader_options,
        }

        match self.type:
            case "video":
                d |= {"height": self.quality}
                d |= {"vcodec": self.codec}
            case "audio":
                d |= {"abr": self.quality}
                d |= {"acodec": self.codec}

        if self.filesize:
            d |= {"filesize": self.filesize}

        return InfoDict(d)

    @classmethod
    def _from_format_entry(cls, format: dict[str, Any]) -> Format:
        type: FORMAT_TYPE = (
            "audio" if format.get("resolution", "") == "audio only" else "video"
        )

        match type:
            case "video":
                quality = format.get("height")
                codec = format.get("vcodec")
            case "audio":
                quality = format.get("abr")
                codec = format.get("acodec")

        return cls(
            url=format["url"],
            id=format["format_id"],
            type=type,
            extension=format["ext"],
            quality=quality or 0,
            codec=codec,
            filesize=format.get("filesize") or None,
            _downloader_options=format.get("downloader_options") or {},
        )

    def __eq__(self, value) -> bool:
        if isinstance(value, Format):
            return self.id == value.id
        else:
            return False


class FormatList(Sequence[Format]):
    """List of formats which can be filtered."""

    def __init__(self, formats: list[Format]) -> None:
        self._formats = formats

    def type(self) -> Literal[FORMAT_TYPE, "incomplete"]:
        """
        Determine main format type.
        It will check if is 'video' or 'audio'.
        """

        if self.filter(type="video"):
            return "video"
        elif self.filter(type="audio"):
            return "audio"
        else:
            return "incomplete"

    def filter(
        self,
        type: FORMAT_TYPE | None = None,
        extension: str | None = None,
        quality: int | None = None,
        codec: str | None = None,
    ) -> FormatList:
        """Get filtered format list by provided options."""

        formats = self._formats

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
        """Sort list by `Format` attribute."""

        has_attribute = [f for f in self._formats if getattr(f, attribute) is not None]
        sorted_list = sorted(
            has_attribute, key=lambda f: getattr(f, attribute), reverse=reverse
        )
        return FormatList(sorted_list)

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
        """Get `Format` with closest quality provided."""

        self = self.sort_by("quality")

        all_qualities = [i.quality for i in self]
        pos = bisect.bisect_left(all_qualities, quality)

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
        new_list = [
            Format._from_format_entry(format)
            for format in info.get("formats") or {}
            if format["ext"] != "mhtml"
        ]
        return FormatList(new_list)

    def __rich_repr__(self):
        yield self._formats

    def __bool__(self):
        return True if self._formats else False

    def __iter__(self):
        for f in self._formats:
            yield f

    def __contains__(self, other) -> bool:
        if isinstance(other, Format) and self.get_by_id(other.id):
            return True
        else:
            return False

    def __len__(self) -> int:
        return len(self._formats)

    @overload
    def __getitem__(self, index: int) -> Format: ...

    @overload
    def __getitem__(self, index: slice) -> FormatList: ...

    def __getitem__(self, index):
        if isinstance(index, slice):
            return FormatList(self._formats[index])
        else:
            return self._formats[index]
