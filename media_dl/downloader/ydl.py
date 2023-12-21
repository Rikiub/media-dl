from typing import cast, Callable, TypedDict, Literal
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


class ProgressHookDict(TypedDict):
    status: Literal["downloading", "finished"]


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
            "outtmpl": "%(uploader)s - %(title)s.%(ext)s",
            "logger": fake_logger,
        }
        formats = gen_format_opts(extension, quality)
        self._ydl = YoutubeDL(opts | formats)

    def _prepare_tempjson(self, data: Result) -> Path:
        return self.tempdir / str(data.source + " " + data.id + ".info.json")

    def _save_result_info(self, data: Result, info_dict: dict) -> None:
        file = self._prepare_tempjson(data)
        file.write_text(json.dumps(info_dict))

    def _get_result_info(self, data: Result) -> Path | None:
        file = self._prepare_tempjson(data)
        if file.is_file():
            return file

    def _get_info_dict(self, url: str) -> dict | None:
        if info := self._ydl.extract_info(url, download=False):
            info = cast(dict, info)

            if info["extractor_key"] == "Generic":
                info.update(
                    {
                        "title": info["webpage_url_domain"],
                        "id": info["webpage_url_basename"],
                    }
                )
                return info

            if entries := info.get("entries"):
                serialize = []
                for item in entries:
                    if item.get("ie_key") and item.get("id") and item.get("title"):
                        serialize.append(item)

                if not serialize:
                    return None

                info["entries"] = serialize

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

        def get_thumbnail(info_dict: dict) -> str | None:
            return (
                info_dict.get("thumbnail")
                or info_dict.get("thumbnails")
                and info_dict["thumbnails"][-1]["url"]
                or None
            )

        if info := self._get_info_dict(url):
            if entries := info.get("entries"):
                entries = cast(list[dict], entries)

                item_list: list[Result] = []

                for item in entries:
                    item_list.append(
                        Result(
                            url=URL(
                                original=item["url"],
                                download=item["url"],
                                thumbnail=get_thumbnail(item),
                            ),
                            source=item["ie_key"],
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
                    source=info["extractor_key"],
                    id=info["id"],
                    title=info["title"],
                    count=info["playlist_count"],
                    entries=item_list,
                )
            else:
                item = Result(
                    url=URL(
                        original=info["original_url"],
                        download=info["url"],
                        thumbnail=get_thumbnail(info),
                    ),
                    source=info["extractor_key"],
                    id=info["id"],
                    title=info["title"],
                    uploader=info.get("uploader", "unkdown"),
                    duration=info.get("duration", 0),
                )
                self._save_result_info(item, info)
                return item
        else:
            return None

    def download(
        self,
        data: Result,
        exist_ok: bool = True,
        on_progress: Callable[[ProgressHookDict], None] | None = None,
    ) -> Path:
        if on_progress:
            ydl = copy(self._ydl)
            ydl._progress_hooks = [on_progress]
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
            if data.source == "Generic":
                ydl.download(data.url.download)
            else:
                ydl.process_ie_result(info_dict, download=True)
        except DownloadError:
            raise

        return final_path


if __name__ == "__main__":
    from rich import print

    def progress_hook(d):
        ...

    url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"

    print("YDL")

    ydl = YDL("temp", "m4a")
    data = ydl.extract_url(url)

    if isinstance(data, Playlist):
        for item in data:
            ydl.download(item, on_progress=progress_hook)
    elif isinstance(data, Result):
        ydl.download(data)
