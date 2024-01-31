from typing import cast, get_args, Callable, NewType, Any
from pathlib import Path
from copy import copy
import logging
import json

from yt_dlp import YoutubeDL, DownloadError

from media_dl.types import (
    Media,
    Playlist,
    ResultType,
    EXTENSION,
    EXT_VIDEO,
    EXT_AUDIO,
    QUALITY,
)
from media_dl.config import DIR_TEMP


fake_logger = logging.getLogger("YoutubeDL")
fake_logger.disabled = True

InfoDict = NewType("InfoDict", dict[str, Any])

_THUMB_COMPATIBLE = {
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


class YDL:
    """
    Arguments:
        extension (str): Prefered file extension type.
        quality (str, int): Prefered file quality. Must be compatible with `extension`.
            Range between [1-9] for audio; Resolution [144-4320] for video.
    """

    def __init__(
        self,
        output: Path | str,
        extension: EXTENSION,
        quality: QUALITY = 9,
        exist_ok: bool = True,
    ):
        self.tempdir = DIR_TEMP / "ydl"
        self.tempdir.mkdir(parents=True, exist_ok=True)
        self.outputdir = Path(output)

        self.exist_ok = exist_ok

        opts = {
            "paths": {
                "home": str(self.outputdir),
                "temp": str(self.tempdir),
            },
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "overwrites": False,
            "extract_flat": "in_playlist",
            "outtmpl": "%(uploader)s - %(title)s.%(ext)s",
            "logger": fake_logger,
        }
        formats = self._gen_format_opts(extension, quality)
        self._ydl = YoutubeDL(opts | formats)

    def _gen_format_opts(self, extension: EXTENSION, quality: QUALITY) -> dict:
        """Generate custom YDLOpts by provided arguments.

        Args:
            extension: Wanted file extension. Custom options will be generated by the extension type.
            quality: Wanted file quality. Range between [1-9].

        Raises:
            ValueError: `extension` or `quality` is invalid.
        """
        video_args = get_args(EXT_VIDEO)
        audio_args = get_args(EXT_AUDIO)
        quality_args = get_args(QUALITY)

        if not quality in quality_args:
            raise ValueError(
                "Invalid quality range. Expected int range [1-9].",
            )

        ydl_opts = {
            "final_ext": extension,
            "postprocessors": [
                {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True},
            ],
        }

        if extension in _THUMB_COMPATIBLE:
            ydl_opts["postprocessors"].append(
                {"key": "EmbedThumbnail", "already_have_thumbnail": False}
            )

        # VIDEO
        if extension in video_args:
            video_quality = quality

            ydl_opts.update(
                {
                    "format": f"bestvideo[height<={video_quality}]+bestaudio/bestvideo[height<={video_quality}]/best",
                    "format_sort": [f"ext:{extension}:mp4:mkv:mov"],
                    "writesubtitles": True,
                    "subtitleslangs": "all",
                }
            )
            ydl_opts["postprocessors"] += [
                {"key": "FFmpegVideoConvertor", "preferedformat": extension},
                {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False},
            ]

        # AUDIO
        elif extension in audio_args:
            ydl_opts.update(
                {
                    "format": "bestaudio/best",
                    "format_sort": [f"ext:{extension}:m4a:mp3:ogg"],
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
                    "preferredcodec": extension,
                    "preferredquality": quality,
                    "nopostoverwrites": True,
                }
            )

        # ERROR
        else:
            raise ValueError(
                "Invalid extension type. Expected:\n"
                f"VIDEO: {', '.join(video_args)}\n"
                f"AUDIO: {', '.join(audio_args)}"
            )

        return ydl_opts

    def _prepare_tempjson(self, data: Media) -> Path:
        return self.tempdir / str(data.extractor + " " + data.id + ".info.json")

    def _save_result_info(self, data: Media, info_dict: InfoDict) -> None:
        file = self._prepare_tempjson(data)
        file.write_text(json.dumps(info_dict))

    def _get_result_info(self, data: Media) -> Path | None:
        file = self._prepare_tempjson(data)
        if file.is_file():
            return file

    def _get_info_dict(self, url: str) -> InfoDict | None:
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

    def _get_info_thumbnail(self, info: InfoDict) -> str | None:
        if thumb := info.get("thumbnail"):
            return thumb
        elif thumb := info.get("thumbnails"):
            return thumb[-1]["url"]
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
                thumbnail=self._get_info_thumbnail(info),
                extractor=info["extractor_key"],
                id=info["id"],
                title=info.get("title") or "",
                count=info.get("playlist_count", 0),
                entries=results,
            )

        # Single Result Type
        # Process fully and save cache copy.
        else:
            item = Media(
                url=info.get("original_url") or info.get("url") or "",
                thumbnail=self._get_info_thumbnail(info),
                extractor=info.get("extractor_key") or info.get("ie_key") or "",
                id=info["id"],
                title=info.get("title") or "",
                uploader=info.get("uploader") or "",
                duration=info.get("duration", 0),
            )
            if info.get("formats"):
                self._save_result_info(item, info)
            return item

    def extract_url(self, url: str) -> ResultType | None:
        """Extract basic information from URL.

        Args:
            url: URL to process.

        Return:
            List of `Media`.
        """

        if info := self._get_info_dict(url):
            return self._info_to_dataclass(info)
        else:
            return None

    def download(
        self,
        data: Media,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Path:
        # Progress Handler
        if progress_callback:
            ydl = copy(self._ydl)
            ydl._progress_hooks = [progress_callback]
        else:
            ydl = self._ydl

        # Load cached file if exist
        if path := self._get_result_info(data):
            info_dict = json.loads(path.read_text())
            path.unlink()
        else:
            info_dict = self._get_info_dict(data.url)

        final_path = Path(ydl.prepare_filename(info_dict))

        # Remove duplicates
        if final_path.is_file():
            if not self.exist_ok:
                raise FileExistsError(final_path)
            return final_path

        # Start download
        try:
            ydl.process_ie_result(info_dict, download=True)
        except DownloadError:
            raise

        return final_path


if __name__ == "__main__":
    from rich import print

    url = "https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth"

    print("YDL")

    ydl = YDL("temp", "m4a")
    data = ydl.extract_url(url)
    print(data)
