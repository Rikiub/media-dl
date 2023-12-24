from typing import cast, Callable, TypedDict
from pathlib import Path
from copy import copy
import logging
import json

from yt_dlp import YoutubeDL, DownloadError

from media_dl.downloader.formats import gen_format_opts
from media_dl.types import URL, Result, Playlist
from media_dl.config import DIR_TEMP

fake_logger = logging.getLogger("YoutubeDL")
fake_logger.disabled = True


class OptionalsInfoDict(TypedDict, total=False):
    playlist_count: int
    thumbnail: str
    thumbnails: list[dict]
    entries: list[dict]


class InfoDict(OptionalsInfoDict):
    id: str
    title: str
    uploader: str
    upload_date: int
    epoch: int
    extractor: str
    extractor_key: str
    url: str
    original_url: str
    webpage_url_basename: str
    webpage_url_domain: str
    formats: list[dict]


class YDL:
    """
    Arguments:
        extension (str): Prefered file extension type.
        quality (str, int): Prefered file quality. Must be compatible with `extension`.
            Range between [0-9] for audio; Resolution [144-5250] for video.
    """

    def __init__(
        self,
        output: Path | str,
        extension: str = "m4a",
        quality: int = 9,
    ):
        self.tempdir = DIR_TEMP / "ydl"
        self.tempdir.mkdir(parents=True, exist_ok=True)
        self.outputdir = Path(output)

        opts = {
            "paths": {
                "home": str(self.outputdir),
                "temp": str(self.tempdir),
            },
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "extract_flat": True,
            "overwrites": False,
            "outtmpl": "%(uploader)s - %(title)s.%(ext)s",
            "logger": fake_logger,
        }
        formats = gen_format_opts(extension, quality)
        self._ydl = YoutubeDL(opts | formats)

    def _prepare_tempjson(self, data: Result) -> Path:
        return self.tempdir / str(data.extractor + " " + data.id + ".info.json")

    def _save_result_info(self, data: Result, info_dict: InfoDict) -> None:
        file = self._prepare_tempjson(data)
        file.write_text(json.dumps(info_dict))

    def _get_result_info(self, data: Result) -> Path | None:
        file = self._prepare_tempjson(data)
        if file.is_file():
            return file

    def _get_info_dict(self, url: str) -> InfoDict | None:
        if info := self._ydl.extract_info(url, download=False):
            # Some extractors redirect the URL to the "real URL",
            # For this extractors we need do another request.
            if info["extractor_key"] == "Generic" and info["url"] != url:
                if aux := self._ydl.extract_info(info["url"], download=False):
                    info = aux

            if entries := info.get("entries"):
                serialize = []
                for item in entries:
                    if item.get("ie_key") and item.get("id") and item.get("title"):
                        serialize.append(item)

                if not serialize:
                    return None

                info["entries"] = serialize

            info = cast(InfoDict, info)
            return info
        else:
            return None

    def extract_url(self, url: str) -> Playlist | Result | None:
        """Extract basic URL information.

        Args:
            url: URL to process.

        Return:
            List of `Result`.
        """

        def get_thumbnail(d: InfoDict | dict) -> str | None:
            if thumb := d.get("thumbnail"):
                return thumb
            elif thumb := d.get("thumbnails"):
                return thumb[-1]["url"]
            else:
                return None

        if info := self._get_info_dict(url):
            # If is Playlist, process as placeholder.
            if entries := info.get("entries"):
                item_list: list[Result] = []

                for item in entries:
                    item_list.append(
                        Result(
                            url=URL(
                                original=item["url"],
                                download=item["url"],
                                thumbnail=get_thumbnail(item),
                            ),
                            extractor=item["ie_key"],
                            id=item["id"],
                            title=item["title"],
                            uploader=item.get("uploader", "unkdown"),
                            duration=item.get("duration", 0),
                        )
                    )
                return Playlist(
                    url=URL(
                        original=info["original_url"],
                        download=info["original_url"],
                        thumbnail=get_thumbnail(info),
                    ),
                    extractor=info["extractor_key"],
                    id=info["id"],
                    title=info["title"],
                    count=info.get("playlist_count", 0),
                    entries=item_list,
                )
            # If is a single item, process full and save its cache.
            else:
                item = Result(
                    url=URL(
                        original=info["original_url"],
                        download=info["url"],
                        thumbnail=get_thumbnail(info),
                    ),
                    extractor=info["extractor_key"],
                    id=info["id"],
                    title=info["title"],
                    uploader=info.get("uploader", "unkdown"),
                    duration=info.get("duration", 0),
                )
                self._save_result_info(item, info)
                return item

        # URL is unsupported.
        else:
            return None

    def download(
        self,
        data: Result,
        exist_ok: bool = True,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> Path:
        if progress_callback:
            ydl = copy(self._ydl)
            ydl._progress_hooks = [progress_callback]
        else:
            ydl = self._ydl

        if path := self._get_result_info(data):
            info_dict = json.loads(path.read_text())
            path.unlink()
        else:
            info_dict = self._get_info_dict(data.url.download)

        final_path = Path(ydl.prepare_filename(info_dict))

        if final_path.is_file():
            if not exist_ok:
                raise FileExistsError(final_path)
            return final_path

        try:
            ydl.process_ie_result(info_dict, download=True)
        except DownloadError:
            raise

        return final_path


if __name__ == "__main__":
    from rich import print

    url = "https://youtu.be/yoMkbDS9RtU?si=5dxxXQzTAp11avxc"

    print("YDL")

    ydl = YDL("temp", "m4a")
    data = ydl.extract_url(url)

    if isinstance(data, Playlist):
        for item in data:
            ydl.download(item)
    elif isinstance(data, Result):
        ydl.download(data)
