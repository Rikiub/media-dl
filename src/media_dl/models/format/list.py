from __future__ import annotations

import bisect
from functools import cached_property
from typing import Generic, Literal

from pydantic import OnErrorOmit
from typing_extensions import Self, TypeVar

from media_dl.models.base import BaseList
from media_dl.models.format.codecs import get_codec_rank
from media_dl.models.format.types import AudioFormat, Format, VideoFormat
from media_dl.types import FORMAT_TYPE


def format_sort(format: Format):
    filesize = format.filesize or 0

    if isinstance(format, VideoFormat):
        is_video = 1

        height = format.height
        fps = format.fps or 0

        vcodec = get_codec_rank(format.video_codec, "video")
        acodec = get_codec_rank(format.audio_codec, "audio")

        return (
            is_video,
            height,
            fps,
            vcodec,
            acodec,
            filesize,
        )

    elif isinstance(format, AudioFormat):
        is_video = 0

        bitrate = format.bitrate
        acodec = get_codec_rank(format.codec, "audio")

        return (
            is_video,
            acodec,
            filesize,
            bitrate,
        )


FormatType = OnErrorOmit[VideoFormat | AudioFormat]
F = TypeVar("F", bound=Format)


class FormatList(BaseList[FormatType], Generic[F]):
    """List of formats which can be filtered."""

    def filter(
        self,
        extension: str | None = None,
        quality: int | None = None,
        codec: str | None = None,
        protocol: str | None = None,
    ) -> Self:
        """Get filtered formats by options."""

        formats = self.root
        filters = [
            (extension, lambda f: f.extension == extension),
            (quality, lambda f: f.quality == quality),
            (codec, lambda f: f.codec.startswith(codec)),
            (protocol, lambda f: f.protocol == protocol),
        ]

        for value, condition in filters:
            if value:
                formats = [f for f in formats if condition(f)]

        return self.__class__(formats)

    def only_video(self) -> FormatList[VideoFormat]:
        return FormatList[VideoFormat](
            [f for f in self.root if isinstance(f, VideoFormat)]
        )

    def only_audio(self) -> FormatList[AudioFormat]:
        return FormatList[AudioFormat](
            [f for f in self.root if isinstance(f, AudioFormat)]
        )

    @cached_property
    def type(self) -> FORMAT_TYPE:
        """
        Determine main format type.
        It will check if is 'video' or 'audio'.
        """

        if self.only_video():
            return "video"
        elif self.only_audio():
            return "audio"
        else:
            return "video"

    def sort_by(
        self,
        attribute: Literal["best", "extension", "quality", "codec", "protocol"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Format` attribute."""

        if attribute == "best":
            filter = format_sort
        elif attribute == "codec":
            filter = lambda codec: get_codec_rank(codec, self.type)  # noqa: E731
        else:
            filter = lambda f: getattr(f, attribute)  # noqa: E731

        return self.__class__(
            sorted(
                self.root,
                key=filter,  # type: ignore
                reverse=reverse,
            )
        )

    def get_by_id(self, id: str) -> F:
        """Get `Format` by `id`.

        Raises:
            IndexError: Provided id has not been founded.
        """

        if result := [f for f in self if f.id == id]:
            return result[0]  # type: ignore
        else:
            raise IndexError(f"Format with id '{id}' has not been founded")

    def get_closest_quality(self, quality: int) -> F:
        items = self.sort_by("quality", reverse=False)
        qualities = [i.quality for i in items]
        pos = bisect.bisect_left(qualities, quality)

        if pos == 0:
            return items[0]  # type: ignore
        if pos == len(items):
            return items[-1]  # type: ignore

        before = items[pos - 1]
        after = items[pos]

        if (after.quality - quality) <= (quality - before.quality):
            return after  # type: ignore
        return before  # type: ignore

    def __contains__(self, other) -> bool:
        if isinstance(other, Format):
            try:
                self.get_by_id(other.id)
                return True
            except IndexError:
                return False
        else:
            return False
