"""Base class for all providers.

Functions: 
- Get results from query/URL and return DataInfo object.
- Download from `Result` object.
"""

from pathlib import Path
from typing import cast
import logging

from yt_dlp import YoutubeDL, DownloadError

from media_dl.config import DIR_TEMP
from media_dl.types import Result, MEDIA_TYPE
from media_dl.providers._ydl_helper import gen_format_opts

fake_logger = logging.getLogger("YoutubeDL")
fake_logger.disabled = True

URL_BASE = ["https://"]


class YDLGeneric:
    """
    Arguments:
        extension (str): Prefered file extension type.
        quality (str, int): Prefered file quality. Must be compatible with `extension`.
            Range between [0-9] for audio; Resolution [144-5250] for video.
    """

    TYPE: MEDIA_TYPE = "video/audio"

    def __init__(self, extension: str = "m4a", quality: int = 9):
        opts = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "extract_flat": True,
            "outtmpl": str(DIR_TEMP / "%(id)s.%(ext)s"),
            "logger": fake_logger,
        }
        opts = gen_format_opts(opts, extension, quality)
        self.ydl = YoutubeDL(opts)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @staticmethod
    def is_url_compatible(url: str) -> bool:
        for item in URL_BASE:
            if url.startswith(item):
                return True
        return False

    def download(self, url: str) -> Path:
        if data := self.ydl.extract_info(url, download=True):
            filename = self.ydl.prepare_filename(data)
            return Path(filename)
        else:
            return Path()

    def search(self, query: str) -> list[Result]:
        raise NotImplementedError

    def extract_url(self, url: str) -> list[Result]:
        """Extract URL information.

        Return:
            List of `Result`.
        """

        def get_thumbnail(info_dict: dict) -> str | None:
            return (
                info_dict.get("thumbnail")
                or info_dict.get("thumbnails")
                and info_dict["thumbnails"][-1]["url"]
                or None
            )

        item_list: list[Result] = []

        while True:
            if info := self.ydl.extract_info(url, download=False):
                info = cast(dict, info)

                if info["extractor"] == "generic":
                    break

                if entries := info.get("entries"):
                    entries = cast(list[dict], entries)

                    if not any(entries):
                        break

                    for item in entries:
                        item_list.append(
                            Result(
                                type=self.TYPE,
                                source="ydl-" + item["ie_key"],
                                id=item["id"],
                                title=item.get("title", None),
                                uploader=item.get("uploader", None),
                                duration=item.get("duration", None),
                                url=item["url"],
                                thumbnail_url=get_thumbnail(item),
                            )
                        )
                else:
                    item_list.append(
                        Result(
                            type=self.TYPE,
                            source="ydl-" + info["extractor_key"],
                            id=info["id"],
                            title=info.get("title", None),
                            uploader=info.get("uploader", None),
                            duration=info.get("duration", None),
                            url=info["original_url"],
                            thumbnail_url=get_thumbnail(info),
                        )
                    )
                break
        return item_list
