from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import bisect

from media_dl.models.base import InfoDict, MetaID, extract_meta

from media_dl.download.format_config import FORMAT_TYPE


@dataclass(slots=True, frozen=True, order=True)
class Format(MetaID):
    format_id: str
    type: FORMAT_TYPE
    extension: str
    quality: int = 0
    codec: str | None = None
    filesize: int | None = None

    @property
    def display_quality(self) -> str:
        if self.type == "video":
            return str(self.quality) + "p"
        elif self.type == "only-audio":
            return str(round(self.quality)) + "kbps"
        else:
            raise TypeError(self.type)

    @classmethod
    def from_info_format(cls, info: InfoDict, format: dict) -> Format:
        type: FORMAT_TYPE = (
            "only-audio" if format.get("resolution", "") == "audio only" else "video"
        )
        extension = format["ext"]

        match type:
            case "video":
                quality = format.get("height")
                codec = format.get("vcodec")
            case "only-audio":
                quality = format.get("abr")
                codec = format.get("acodec")

        return cls(
            *extract_meta(info),
            format_id=format["format_id"],
            type=type,
            extension=extension,
            quality=quality or 0,
            codec=codec,
            filesize=format.get("filesize") or None,
        )


class FormatList(list[Format]):
    def guess_type(self) -> Literal[FORMAT_TYPE, "incomplete"]:
        """
        Determine main format type.
        It'll check if is video or audio.
        """

        if self.filter(type="video"):
            return "video"
        elif self.filter(type="only-audio"):
            return "only-audio"
        else:
            return "incomplete"

    def filter(
        self,
        type: FORMAT_TYPE | None = None,
        extension: str | None = None,
        quality: int | None = None,
        codec: str | None = None,
    ) -> FormatList:
        if type:
            self = FormatList(f for f in self if f.type == type)
        if extension:
            self = FormatList(f for f in self if f.extension == extension)
        if quality:
            self = FormatList(f for f in self if f.quality == quality)
        if codec:
            self = FormatList(f for f in self if f.codec and f.codec.startswith(codec))

        return self

    def sort_by(self, attribute: str, reverse: bool = False) -> FormatList:
        has_attribute = [f for f in self if getattr(f, attribute) is not None]
        return FormatList(
            sorted(has_attribute, key=lambda f: getattr(f, attribute), reverse=reverse)
        )

    def get_by_id(self, id: str) -> Format | None:
        if result := [f for f in self if f.format_id == id]:
            return result[0]
        else:
            return None

    def get_best_quality(self) -> Format:
        formats = self.sort_by("quality")
        return formats[-1]

    def get_worst_quality(self) -> Format:
        formats = self.sort_by("quality")
        return formats[0]

    def get_closest_quality(self, quality: int) -> Format:
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
    def from_info(cls, info: InfoDict) -> FormatList:
        return cls(
            Format.from_info_format(info, format)
            for format in info.get("formats") or {}
        )
