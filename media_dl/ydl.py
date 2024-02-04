from typing import cast, get_args, Callable, NewType, Any
from pathlib import Path
from copy import copy
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
    FORMAT_TYPE,
    EXT_VIDEO,
    EXT_AUDIO,
    EXTENSION,
    QUALITY,
    VIDEO_RES,
)
from media_dl.config import DIR_TEMP


supress_logger = logging.getLogger("YoutubeDL")
supress_logger.disabled = True

InfoDict = NewType("InfoDict", dict[str, Any])

THUMB_COMPATIBLE_EXTS = {
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


def get_info_thumbnail(info: InfoDict) -> str:
    if thumb := info.get("thumbnail"):
        return thumb
    elif thumb := info.get("thumbnails"):
        return thumb[-1]["url"]
    else:
        return ""


class YDL:
    """
    yt-dlp helper with nice defaults. It will handle:

    - Info extraction from supported URLs
    - `Media` objects creation
    - Request files to download, conversion, metadata, etc

    Arguments:
        output: Directory where to save downloaded files.
        format: File to request.
        - Select 'best-video/best-audio' will try get the best file without convert it.
        - Select one extension type will convert the file (It is slow and may increase file size without any quality difference).

        quality: File quality. Range between [1-9]. By default will select the best quality [9].
    """

    def __init__(
        self,
        output: Path | str,
        format: FORMAT_TYPE | EXTENSION,
        quality: QUALITY = 9,
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
        quality_range = get_args(QUALITY)

        if not quality in quality_range:
            raise ValueError(
                f"'{quality}' is out of range. Expected int range [1-9].",
            )

        # VIDEO
        if format == "best-video" or format in video_exts:
            video_quality = get_args(VIDEO_RES)[quality - 1]

            ydl_opts.update(
                {
                    "format": f"bv[height<={video_quality}]+ba/bv[height<={video_quality}]/b",
                    "merge_output_format": "/".join(video_exts),
                    "subtitleslangs": "all",
                    "writesubtitles": True,
                }
            )

            if format in video_exts:
                ydl_opts["postprocessors"].append(
                    {"key": "FFmpegVideoConvertor", "preferedformat": format}
                )
        # AUDIO
        elif format == "best-audio" or format in audio_exts:
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
                    "preferredcodec": format if format in audio_exts else None,
                    "preferredquality": quality if quality != 9 else None,
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
            raise ValueError(
                f"'{format}' is invalid. Excepted 'best-video', 'best-audio' or one 'extension': "
                + ", ".join(video_exts + audio_exts),
            )

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

            # Check if is a valid Playlist
            if entries := info.get("entries"):
                serialize = []

                for item in entries:
                    # If item has the 2 required fields, will be added.
                    if item.get("ie_key") and item.get("id"):
                        serialize.append(item)

                if not serialize:
                    return None
            # Check at least if is a valid Result
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
                thumbnail=get_info_thumbnail(info),
                extractor=info["extractor_key"],
                id=info["id"],
                title=info.get("title") or "",
                count=info.get("playlist_count") or 0,
                entries=results,
            )

        # Single Result Type
        # Process fully and save cache copy.
        else:
            item = Media(
                url=info.get("original_url") or info.get("url") or "",
                thumbnail=get_info_thumbnail(info),
                extractor=info.get("extractor_key") or info.get("ie_key") or "",
                id=info["id"],
                title=info.get("title") or "",
                creator=info.get("uploader") or "",
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

    url = "https://music.youtube.com/watch?v=Kx7B-XvmFtE"
    print("> Using YDL")

    ydl = YDL("temp", "best-video")
    data = ydl.extract_url(url)
    print(data)

    if isinstance(data, Media):
        ydl.download(data)
    elif isinstance(data, Playlist):
        for item in data:
            ydl.download(item)
