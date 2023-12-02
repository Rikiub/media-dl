from typing import Callable, NewType, cast
from dataclasses import dataclass
import concurrent.futures as cf
from pathlib import Path
import json

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from yt_dlp.extractor import gen_extractors

__all__ = ["FORMAT_EXTS", "QUALITY", "YDL"]

FORMAT_EXTS: dict = YoutubeDL._format_selection_exts
PROVIDERS = {
    "soundcloud": "scsearch:",
    "youtube": "ytsearch:",
    "ytmusic": "https://music.youtube.com/search?q=",
    "bilibili": "bilisearch:",
    "nicovideo": "nicosearch:",
    "rokfin": "rkfnsearch:",
    "yahoo": "yvsearch:",
    "googlevideo": "gvsearch:",
    "netverse": "netsearch:",
    "prxstories": "prxstories:",
    "prxseries": "prxseries:",
}
QUALITY = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
DEFAULT_QUALITY = 9

InfoDict = NewType("InfoDict", dict)
YDLOpts = NewType("YDLOpts", dict)


class ExtTypeError(Exception):
    """Handler to EXT type errors"""


class QualityTypeError(Exception):
    """Handler to quality"""


class FakeLogger:
    """Supress yt-dlp output"""

    @staticmethod
    def error(msg):
        pass

    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def debug(msg):
        pass


@dataclass(slots=True)
class IEData:
    """InfoExtractor dict but more simple and dynamic."""

    url: str
    id: str
    extractor: str
    title: str
    creator: str | None = None
    thumbnail_url: str | None = None
    _info_dict: InfoDict | None = None

    @property
    def info_dict(self) -> InfoDict:
        self.generate_info_dict(force_process=False)
        info_dict = cast(InfoDict, self._info_dict)
        return info_dict

    def generate_info_dict(self, force_process=False) -> None:
        """Fill missed data if not found info_dict.

        Raises:
            ConnectionError: Can't fetch the info_dict.
        """

        ydl = YDL(quiet=True)
        if self._info_dict and not force_process:
            pass
        else:
            if info_dict := ydl._get_info_dict(self.url):
                self.creator = info_dict.get("uploader", self.creator)
                self.thumbnail_url = info_dict.get("thumbnail", self.thumbnail_url)
                self._info_dict = info_dict
            else:
                raise DownloadError("Failed to fetch info data.")


@dataclass(slots=True)
class IEPlaylist:
    url: str
    id: str
    extractor: str
    title: str
    total_count: int
    ie_list: list[IEData]

    def fetch_ie_all(self) -> None:
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            try:
                futures = [
                    pool.submit(item.generate_info_dict) for item in self.ie_list
                ]
                cf.wait(futures)
            except DownloadError:
                pool.shutdown(wait=False)
                raise


class YDL:
    """module main class"""

    def __init__(
        self,
        quiet: bool = False,
        logger: Callable | None = None,
        cachedir: Path | None = None,
    ):
        if not cachedir:
            cachedir = Path("").absolute()

        self.cachedir = cachedir

        self.ydl_opts: dict = {
            "paths": {
                "home": "",
                "temp": str(cachedir),
            },
            "quiet": quiet,
            "noprogress": quiet,
            "no_warnings": quiet,
            "ignoreerrors": False,
            "skip_download": False,
            "overwrites": False,
            "extract_flat": True,
            "retries": 3,
            "fragment_retries": 3,
            "outtmpl": "%(uploader)s - %(title)s.%(ext)s",
            "postprocessors": [],
        }

        if logger:
            self.ydl_opts.update({"logger": logger})
        elif quiet:
            self.ydl_opts.update({"logger": FakeLogger})

    @staticmethod
    def is_url_supported(url: str) -> bool:
        extractor = gen_extractors()
        for e in extractor:
            if e.suitable(url) and e.IE_NAME != "generic":
                return True
        return False

    def _prepare_filename(self, info: IEData, ydl_opts: YDLOpts) -> Path:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = info.info_dict
            info_dict["ext"] = ydl_opts["final_ext"]
            filename = ydl.prepare_filename(info_dict)
            return Path(filename)

    def _convert_info_dict(
        self, info_dict: InfoDict, force_process: bool = False
    ) -> IEData | IEPlaylist:
        """Convert yt-dlp info_dict to dataclass object

        Args:
            info_dict: Valid info_dict to parse.
        """

        if "entries" in info_dict:
            ie_list = []

            for item in info_dict["entries"]:
                if not item.get("title"):
                    continue

                thumbnail = (
                    item.get("thumbnail")
                    or item.get("thumbnails")
                    and item["thumbnails"][-1]["url"]
                    or None
                )

                ie_list.append(
                    IEData(
                        url=item["url"],
                        extractor=item["ie_key"],
                        id=item["id"],
                        title=item["title"],
                        creator=item.get("uploader", None),
                        thumbnail_url=thumbnail,
                    )
                )

            if len(ie_list) == 1:
                ie = ie_list[0]
                ie.generate_info_dict()
                return ie
            else:
                playlist = IEPlaylist(
                    url=info_dict["original_url"],
                    id=info_dict["id"],
                    extractor=info_dict["extractor_key"],
                    title=info_dict["title"],
                    total_count=info_dict["playlist_count"],
                    ie_list=ie_list,
                )
                if force_process:
                    playlist.fetch_ie_all()
                return playlist
        else:
            return IEData(
                url=info_dict["original_url"],
                id=info_dict["id"],
                extractor=info_dict["extractor"],
                title=info_dict["title"],
                creator=info_dict.get("uploader", None),
                thumbnail_url=info_dict.get("thumbnail", None),
                _info_dict=info_dict,
            )

    def _get_info_dict(self, url: str, limit: int | None = None) -> InfoDict | None:
        """Fetch info_dict from valid URL"""

        ydl_opts = self.ydl_opts
        if limit:
            ydl_opts.update({"playlist_items": f"0:{limit}"})

        with YoutubeDL(ydl_opts) as ydl:
            try:
                if info := ydl.extract_info(url, download=False):
                    if "entries" in info and not any(info["entries"]):
                        return None
                    return InfoDict(info)
                else:
                    return None
            except DownloadError:
                raise

    def extract_info(
        self, url: str, force_process: bool = False
    ) -> IEData | IEPlaylist | None:
        """Simple search to get a yt-dlp info_dict

        Args:
            url: URL to process.

        Returns:
            If the extraction is succesful, return its info dict, otherwise return None.
        """

        if info := self._get_info_dict(url):
            return self._convert_info_dict(info, force_process=force_process)
        else:
            return None

    def extract_info_from_search(
        self, query: str, provider: str, limit: int = 5, force_process: bool = False
    ) -> list[IEData] | None:
        """Get one/multiple yt-dlp info dict from custom provider like YouTube or SoundCloud.

        Args:
            query: Query to process.
            provider: Provider where do the searchs.
            limit: Max of searchs to do.
        """

        if provider in PROVIDERS.keys():
            provider = PROVIDERS[provider]
        else:
            raise ValueError(
                f"{provider} is not a valid provider. Available options:",
                PROVIDERS.keys(),
            )

        if info := self._get_info_dict(f"{provider}{query}", limit=limit):
            if (
                data := self._convert_info_dict(info, force_process=force_process)
            ) and isinstance(data, IEPlaylist):
                return [item for item in data.ie_list]
            else:
                return [data]
        else:
            return None

    def _generate_ydl_opts(
        self,
        output: Path,
        extension: str,
        quality: int = DEFAULT_QUALITY,
    ) -> YDLOpts:
        """Generate custom `ydl_opts` dict by provided arguments.

        Args:
            extension: Wanted file extension. `ydl_opts` options will be generated by the extension type.
            extension_quality: Wanted file quality. Range between [0-9].

        Raises:
            ExtTypeError: `extension` is not compatible.
            QualityTypeError: `extension_quality` is out of range.
        """

        ydl_opts = self.ydl_opts
        ydl_opts["paths"]["home"] = str(output)
        ydl_opts.update({"final_ext": extension})

        # validate `extension_quality`
        if not quality in QUALITY:
            raise QualityTypeError(
                'Failed to determine "quality" range. Expected range between:',
                *QUALITY,
            )

        # embed metadata
        ydl_opts["postprocessors"].append(
            {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True}
        )

        # check if `extension` is thumbnail compatible.
        THUMBNAIL_EXTS = (
            "mp3",
            "mkv",
            "mka",
            "ogg",
            "opus",
            "flac",
            "m4a",
            "mp4",
            "mov",
        )
        if extension in THUMBNAIL_EXTS:
            ydl_opts.update(
                {
                    "writethumbnail": True,
                }
            )
            ydl_opts["postprocessors"].append(
                {"key": "EmbedThumbnail", "already_have_thumbnail": False}
            )

        # VIDEO
        if extension in FORMAT_EXTS["video"]:
            VIDEO_QUALITY = (
                "144",
                "240",
                "360",
                "480",
                "720",
                "1080",
                "1440",
                "2160",
                "4320",
                "5250",
            )
            new_quality = VIDEO_QUALITY[quality]

            ydl_opts.update(
                {
                    "format": f"bestvideo[height<={new_quality}]+bestaudio/bestvideo[height<={new_quality}]/best",
                    "format_sort": [f"ext:{extension}:mp4:mkv:mov"],
                    "writesubtitles": True,
                    "subtitleslangs": "all",
                }
            )
            ydl_opts["postprocessors"].append(
                {"key": "FFmpegVideoConvertor", "preferedformat": extension}
            )
            ydl_opts["postprocessors"].append(
                {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False},
            )

        # AUDIO
        elif extension in FORMAT_EXTS["audio"]:
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
            if quality in QUALITY:
                ydl_opts["postprocessors"].append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": extension,
                        "preferredquality": quality,
                        "nopostoverwrites": False,
                    }
                )

        else:
            raise ExtTypeError(
                'Failed to determine the "extension" type. Expected:',
                "VIDEO:",
                FORMAT_EXTS["video"],
                "AUDIO:",
                FORMAT_EXTS["audio"],
            )

        return YDLOpts(ydl_opts)

    def download(
        self,
        query: str | list[IEData] | IEData | IEPlaylist,
        extension: str,
        quality: int = DEFAULT_QUALITY,
        output: Path = Path.cwd(),
        exist_ok: bool = True,
        progress: list[Callable] | bool = True,
    ) -> None:
        """Generate custom config by `extension` type and download.

        Args:
            query: String with a supported yt-dlp URL. Use `IEData` as cache.
            extension: Prefered file extension.
            quality: Prefered file quality. Default is max quality (9).
            output_path: Directory where save the downloads. Default is cwd.
            exist_ok: Ignore exception if one file exist in output.
            progress: Callable which can get download information.

        Raises:
            DownloadError: When yt-dlp throw an error.
            FileExistsError: If exist_ok is set, throw error when the file exist in output.
        """

        # set custom ydl_opts
        ydl_opts = self._generate_ydl_opts(
            output=output, extension=extension, quality=quality
        )

        if isinstance(progress, bool):
            ydl_opts.update({"noprogress": not progress})
        else:
            ydl_opts.update({"progress_hooks": progress, "noprogress": True})

        # start download
        try:
            downloads: list[IEData] = []

            # Convert URL string to IE object.
            if isinstance(query, str):
                if info := self.extract_info(query):
                    query = info
                else:
                    raise DownloadError("Failed to fetch data.")

            if isinstance(query, IEData):
                downloads.append(query)
            elif isinstance(query, IEPlaylist):
                for item in query.ie_list:
                    downloads.append(item)
            elif isinstance(query, list):
                for item in query:
                    downloads.append(item)
            else:
                raise ValueError(
                    f"Must be `str`, `list[IEData]`, `IEData` or `IEPlaylist` object."
                )

            with YoutubeDL(params=ydl_opts) as ydl:
                for item in downloads:
                    temp = Path(self.cachedir / f"{item.extractor} {item.id}")
                    temp.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        filename = self._prepare_filename(item, ydl_opts)
                        if filename.is_file():
                            if not exist_ok:
                                raise FileExistsError(filename.name)
                            continue

                        info = item.info_dict
                        temp.write_text(json.dumps(info))
                        ydl.download_with_info_file(temp)
                    finally:
                        temp.unlink(missing_ok=True)
        except DownloadError:
            raise


if __name__ == "__main__":
    from rich import print

    ydl = YDL(quiet=True, cachedir=Path("/tmp/media-dl"))

    print("> Playlist + Errors")
    if info := ydl.extract_info(
        "https://www.youtube.com/playlist?list=PL59FEE129ADFF2B12",
    ):
        print(info)

        print("> Downloading...")
        ydl.download(info, "m4a")

    print("> Playlist")
    if info := ydl.extract_info(
        "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI",
    ):
        print(info)

    print("> Single Video")
    if info := ydl.extract_info("https://www.youtube.com/watch?v=BaW_jenozKc"):
        print(info)

    print("> Custom Search")
    if info := ydl.extract_info_from_search(
        "Sub Urban - Rabbit Hole", provider="youtube", limit=5
    ):
        print(info)
    else:
        print("Not results")
