from typing import Literal, NewType, Any
from dataclasses import dataclass

InfoDict = NewType("InfoDict", dict[str, Any])


@dataclass(slots=True)
class _ExtractID:
    extractor: str
    id: str
    url: str


@dataclass(slots=True, frozen=True)
class Format:
    url: str
    id: str
    format: str
    extension: str
    vcodec: str | None
    acodec: str | None

    def __post__init__(self):
        if not (self.vcodec or self.acodec):
            raise ValueError("Must have a codec.")


@dataclass(slots=True)
class Media(_ExtractID):
    thumbnail: str
    title: str
    creator: str
    duration: int
    formats: list[Format]

    @staticmethod
    def _gen_formats(info: InfoDict) -> list["Format"]:
        results = []

        for format in info.get("formats") or {}:
            try:
                fmt = Format(
                    url=format["url"],
                    id=format["format_id"],
                    format=format["resolution"],
                    extension=format["ext"],
                    vcodec=format["vcodec"] if format["vcodec"] != "none" else None,
                    acodec=format["acodec"] if format["acodec"] != "none" else None,
                )
                results.append(fmt)
            except KeyError:
                continue

        return results

    @classmethod
    def from_info(cls, info: InfoDict) -> "Media":
        if info.get("entries"):
            raise TypeError(
                "Provided InfoDict is a playlist. Playlists is not allowed."
            )

        return Media(
            extractor=info.get("extractor_key") or info["ie_key"],
            id=info["id"],
            url=info.get("original_url") or info["url"],
            thumbnail=info.get("thumbnail") or "",
            title=info.get("track") or info.get("title") or "",
            creator=(
                info.get("artist")
                or info.get("channel")
                or info.get("creator")
                or info.get("uploader")
                or ""
            ),
            duration=info.get("duration") or 0,
            formats=cls._gen_formats(info),
        )

    def format_type(
        self,
    ) -> Literal["video+audio", "only_video", "only_audio", "incomplete"]:
        video_audio = False
        only_video = False
        only_audio = False

        for item in self.formats:
            if item.vcodec and item.acodec:
                video_audio = True
            elif item.vcodec:
                only_video = True
            elif item.acodec:
                only_audio = True

        if video_audio:
            return "video+audio"
        elif only_video:
            return "only_video"
        elif only_audio:
            return "only_audio"
        else:
            return "incomplete"

    def is_complete(self) -> bool:
        if self.formats:
            return True
        else:
            return False


@dataclass(slots=True)
class Playlist(_ExtractID):
    thumbnail: str
    title: str
    count: int
    entries: list[Media]

    @classmethod
    def from_info(cls, info: InfoDict) -> "Playlist":
        if not info.get("entries"):
            raise TypeError("Provided InfoDict is a single item, not a playlist.")

        results = []

        for entry in info["entries"]:
            data = Media.from_info(entry)
            results.append(data)

        return Playlist(
            extractor=info["extractor_key"],
            id=info["id"],
            url=info.get("original_url") or info["url"],
            thumbnail=info.get("thumbnail") or "",
            title=info.get("title") or "",
            count=info["playlist_count"],
            entries=results,
        )

    def __len__(self):
        return self.count

    def __iter__(self):
        for item in self.entries:
            yield item


ResultType = Media | Playlist | list[Media]
