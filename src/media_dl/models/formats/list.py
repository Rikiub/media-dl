from __future__ import annotations

import bisect
from functools import cached_property
from typing import Generic, Literal, overload

from pydantic import OnErrorOmit, RootModel
from typing_extensions import Self, TypeVar

from media_dl.models.formats.codecs import get_codec_rank
from media_dl.models.formats.types import AudioFormat, Format, FormatType, VideoFormat
from media_dl.types import FORMAT_TYPE

F = TypeVar("F", default=Format)


def format_sort(format: FormatType):
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


class FormatList(RootModel[list[OnErrorOmit[FormatType]]], Generic[F]):
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

        return FormatList(formats)  # type: ignore

    def only_video(self) -> FormatList[VideoFormat]:
        return FormatList([f for f in self.root if isinstance(f, VideoFormat)])

    def only_audio(self) -> FormatList[AudioFormat]:
        return FormatList([f for f in self.root if isinstance(f, AudioFormat)])

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
        else:
            filter = lambda f: getattr(f, attribute)  # noqa: E731

        return self.__class__(
            sorted(
                self.root,
                key=filter,
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
            return items[0]
        if pos == len(items):
            return items[-1]

        before = items[pos - 1]
        after = items[pos]

        if (after.quality - quality) <= (quality - before.quality):  # type: ignore
            return after
        return before

    def __contains__(self, other) -> bool:
        if isinstance(other, Format):
            try:
                self.get_by_id(other.id)
                return True
            except IndexError:
                return False
        else:
            return False

    def __iter__(self):  # type: ignore
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __bool__(self) -> bool:
        return bool(self.root)

    @overload
    def __getitem__(self, index: int) -> F: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    def __getitem__(self, index) -> F | Self:
        match index:
            case int():
                return self.root[index]  # type: ignore
            case slice():
                return self.__class__(self.root[index])
            case _:
                raise TypeError(index)
