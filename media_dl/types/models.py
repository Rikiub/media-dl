from typing import Literal, NewType, Any
from dataclasses import dataclass

InfoDict = NewType("InfoDict", dict[str, Any])


@dataclass(slots=True)
class _BaseID:
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
class Media(_BaseID):
    thumbnail: str
    title: str
    creator: str
    duration: int
    formats: set[Format]

    @staticmethod
    def _gen_formats(info: InfoDict) -> set["Format"]:
        results = set()

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
                results.add(fmt)
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
        type = "incomplete"

        for item in self.formats:
            if item.vcodec and item.acodec:
                type = "video+audio"
                break
            elif item.vcodec:
                type = "only_video"
                break
            elif item.acodec:
                type = "only_audio"
                break

        return type

    def is_complete(self) -> bool:
        if self.formats:
            return True
        else:
            return False


@dataclass(slots=True)
class Playlist(_BaseID):
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
