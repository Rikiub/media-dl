from typing import Generator, Literal, cast, get_args, Callable, NewType, Any
from pathlib import Path
from copy import copy
from enum import Enum
import logging
import json

from yt_dlp import YoutubeDL, DownloadError
from yt_dlp.postprocessor import PostProcessor
from mutagen._file import FileType
import syncedlyrics
import music_tag

from media_dl.types import (
    Media,
    Playlist,
    ResultType,
    FORMAT,
    EXT_VIDEO,
    EXT_AUDIO,
    EXTENSION,
    VIDEO_RES,
    AUDIO_QUALITY,
)
from media_dl.config import DIR_TEMP


supress_logger = logging.getLogger("YoutubeDL")
supress_logger.disabled = True

InfoDict = NewType("InfoDict", dict[str, Any])

_THUMB_COMPATIBLE_EXTS = {
    "mp3",
    "mkv",
    "mka",
    "ogg",
    "opus",
    "flac",
    "m4a",
    "mp4",
    "mov",
}
_SEARCH_LIMIT = "20"


class SearchProvider(Enum):
    ytmusic = "https://music.youtube.com/search?q="
    youtube = "ytsearch" + _SEARCH_LIMIT + ":"
    soundcloud = "scsearch" + _SEARCH_LIMIT + ":"


SEARCH_PROVDER = Literal["ytmusic", "youtube", "soundcloud"]


class MusicMetaPP(PostProcessor):
    SUPPORTED_EXTS = get_args(EXT_AUDIO)

    def run(self, information):
        ext = information["ext"]
        track = information.get("track")
        artist = information.get("artist")

        if ext in self.SUPPORTED_EXTS and track and artist:
            audio = music_tag.load_file(information["filepath"])
            audio = cast(FileType, audio)

            # Fix year tag
            if not audio["year"] or len(str(audio["year"])) > 4:
                year = int(
                    information.get("release_year")
                    or information.get("upload_date")[:4]
                )
                audio["year"] = year
            if not audio["album"]:
                # Single Album
                audio["album"] = track
            if not audio["album_artist"]:
                audio["album_artist"] = artist
            if not audio["lyrics"]:
                try:
                    search_term = track + " - " + artist
                    if lyrics := syncedlyrics.search(
                        search_term, allow_plain_format=True
                    ):
                        audio["lyrics"] = lyrics
                except:
                    pass
            audio.save()

        return [], information


class YDL:
    """
    yt-dlp helper with nice defaults and handler for:

    - Info extraction from supported URLs.
    - `Media` objects creation.
    - Request files to download, conversion, embed metadata, etc.

    Arguments:
        output: Directory where to save downloaded files.
        format: Prefered file to request. Will try get the best file, but if can't get a 'video' file, fallback to 'audio'.
        convert: Convert final file to wanted extension (It is slow and may increase file size).
        video_res: Prefered video resolution. If selected quality is'nt available, closest one is used instead.
        audio_quality: Prefered audio quality when do a file conversion. Range between [1-9].

    Raises:
        ValueEror: Bad provided arguments.
    """

    def __init__(
        self,
        output: Path | str,
        format: FORMAT,
        convert: EXTENSION | None = None,
        video_res: VIDEO_RES = "2160",
        audio_quality: AUDIO_QUALITY = 9,
    ):
        # Instance vars
        self.tempdir = DIR_TEMP / "ydl"
        self.tempdir.mkdir(parents=True, exist_ok=True)
        self.outputdir = Path(output)

        ydl_opts = {
            "paths": {
                "home": str(self.outputdir),
                "temp": str(self.tempdir),
            },
            "outtmpl": {
                "default": "%(artist,creator,uploader)s - %(track,title)s.%(ext)s",
            },
            "ignoreerrors": False,
            "overwrites": False,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "logger": supress_logger,
            "postprocessors": [],
        }

        # Determine extension
        video_exts = get_args(EXT_VIDEO)
        audio_exts = get_args(EXT_AUDIO)
        quality_range = get_args(AUDIO_QUALITY)

        if not audio_quality in quality_range:
            raise ValueError(
                f"'{audio_quality}' is out of range. Expected range between [1-9].",
            )
        if convert:
            if not (format == "video" and convert in video_exts) and not (
                format == "audio" and convert in audio_exts
            ):
                raise ValueError(
                    f"The '{format}' format and the '{convert}' extension to be converted are incompatible."
                )

        # Video
        if format == "video":
            res = video_res if video_res else "5000"
            ydl_opts.update(
                {
                    "format": f"bv[height<={res}]+ba/bv[height<={res}]/b",
                    "merge_output_format": "/".join(video_exts),
                    "subtitleslangs": "all",
                    "writesubtitles": True,
                }
            )

            if convert:
                ydl_opts["postprocessors"].append(
                    {"key": "FFmpegVideoConvertor", "preferedformat": convert}
                )
        # Audio
        elif format == "audio":
            ydl_opts.update(
                {
                    "format": "ba/b",
                    "postprocessor_args": {
                        "thumbnailsconvertor+ffmpeg_o": [
                            "-c:v",
                            "png",
                            "-vf",
                            "crop=ih",
                        ]
                    },
                }
            )

            ydl_opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "nopostoverwrites": True,
                    "preferredcodec": convert if convert in audio_exts else None,
                    "preferredquality": audio_quality if audio_quality != 9 else None,
                }
            )

            """
            # Audio Lyrics support. Would be a new feature, see:
            # https://github.com/yt-dlp/yt-dlp/pull/8869
            postprocessors.append(
                {
                    "key": "FFmpegSubtitlesConvertor",
                    "format": "lrc",
                    "when": "before_dl",
                }
            )
            """
        # Invalid Format
        else:
            raise ValueError(f"'{format}' is invalid. Expected 'video' or 'audio'.")

        # Metadata Postprocessors
        ydl_opts["postprocessors"].append(
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "opus>ogg/aac>m4a/mov>mp4/webm>mkv",
            }
        )
        ydl_opts["postprocessors"].append(
            {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True}
        )
        ydl_opts["postprocessors"].append(
            {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False}
        )
        ydl_opts["postprocessors"].append(
            {"key": "EmbedThumbnail", "already_have_thumbnail": False}
        )

        # Init final YDL
        self._ydl = YoutubeDL(ydl_opts)
        self._ydl.add_post_processor(MusicMetaPP(), when="post_process")

    @staticmethod
    def result_to_iterable(result: ResultType) -> Generator[Media, None, None]:
        match result:
            case Playlist():
                for item in result.entries:
                    yield item
            case Media():
                yield result
            case _:
                raise TypeError()

    def _prepare_tempjson(self, data: Media) -> Path:
        return self.tempdir / str(data.extractor + " " + data.id + ".info.json")

    def save_info(self, data: Media, info_dict: InfoDict) -> None:
        """Save `Media` as cached `InfoDict`"""
        file = self._prepare_tempjson(data)
        file.write_text(json.dumps(info_dict))

    def load_saved_info(self, data: Media) -> InfoDict | None:
        """Get cached `InfoDict` of a `Media` item if exist."""
        file = self._prepare_tempjson(data)
        if file.is_file():
            return json.loads(file.read_text())

    def _fetch_url(self, url: str) -> InfoDict | None:
        """Process and validate yt-dlp URLs"""

        if info := self._ydl.extract_info(url, download=False):
            # Some extractors redirect the URL to the "real URL",
            # For this extractors we need do another request.
            if info["extractor_key"] == "Generic" and info["url"] != url:
                if data := self._ydl.extract_info(info["url"], download=False):
                    info = data

            # Check if is a valid playlist and validate
            if entries := info.get("entries"):
                for item in entries:
                    # If item not has the 2 required fields, will be deleted.
                    if not (item.get("ie_key") and item.get("id")):
                        del item
                if not entries:
                    return None
            # Check at least if is a valid info
            elif not info.get("formats"):
                return None

            info = cast(InfoDict, info)
            return info
        else:
            return None

    def _info_to_dataclass(self, info: InfoDict) -> ResultType:
        # Playlist Type
        if entries := info.get("entries"):
            results = []

            # Recursive add of items
            for item in entries:
                item = self._info_to_dataclass(item)
                results.append(item)

            return Playlist(
                url=info.get("original_url") or info.get("url") or "",
                thumbnail=info.get("thumbnail") or "",
                extractor=info["extractor_key"],
                id=info["id"],
                title=info.get("title") or "",
                count=info.get("playlist_count") or 0,
                entries=results,
            )
        # Single Media Type
        # Process fully and save cache copy.
        else:
            item = Media(
                url=info.get("original_url") or info.get("url") or "",
                thumbnail=info.get("thumbnail") or "",
                extractor=info.get("extractor_key") or info.get("ie_key") or "",
                id=info["id"],
                title=info.get("track") or info.get("title") or "",
                creator=(
                    info.get("artist")
                    or info.get("creator")
                    or info.get("uploader")
                    or ""
                ),
                duration=info.get("duration") or 0,
            )
            if info.get("formats"):
                self.save_info(item, info)
            return item

    def extract_url(self, url: str) -> ResultType | None:
        """Extract basic information from URL.

        Args:
            url: URL to process.

        Return:
            List of `Media`.

        Raises:
            DownloadError: `yt-dlp` related exceptions.
        """

        try:
            info = self._fetch_url(url)
        except DownloadError:
            raise

        if info:
            return self._info_to_dataclass(info)
        else:
            return None

    def search(self, query: str, provider: SEARCH_PROVDER) -> list[Media]:
        result = []

        try:
            prov = SearchProvider[provider].value
        except:
            raise ValueError(f"'{provider}' is invalid.")

        try:
            info = self._fetch_url(prov + query)
        except DownloadError:
            raise

        if info:
            info = self._info_to_dataclass(info)
            if isinstance(info, Playlist):
                result = info.entries

        return result

    def download(
        self,
        data: Media,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Path:
        """Download and get the final path from a `Media` item.

        Raises:
            DownloadError: `yt-dlp` related exceptions.
        """

        # Progress Handler
        if progress_callback:
            ydl = copy(self._ydl)
            ydl._progress_hooks = [progress_callback]
        else:
            ydl = self._ydl

        # Load cached info if exist, else re-fetch info.
        if info := self.load_saved_info(data) or self._fetch_url(data.url):
            info_dict = info
        else:
            raise DownloadError("Unable to fetch info from:", data.url)

        # Start download
        try:
            info_dict = ydl.process_ie_result(info_dict, download=True)
        except DownloadError:
            raise

        final_path = Path(info_dict["requested_downloads"][0]["filepath"])
        return final_path


if __name__ == "__main__":
    from rich import print

    url = "https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth"
    print("> Using YDL")

    ydl = YDL("temp", "video")
    data = ydl.extract_url(url)
    print(data)

    data = ydl.search("Imagine Dragons", "ytmusic")
    print(data)

    """
    if isinstance(data, Media):
        ydl.download(data)
    elif isinstance(data, Playlist):
        for item in data:
            ydl.download(item)
    """
