from typing import cast, Callable, Any, NewType, TypedDict
from dataclasses import dataclass
import concurrent.futures as cf
from pathlib import Path
import json

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from yt_dlp.extractor import gen_extractors


class FormatExtsDict(TypedDict):
    video: set[str]
    audio: set[str]
    storyboards: set[str]


FORMAT_EXTS = cast(FormatExtsDict, YoutubeDL._format_selection_exts)
_THUMBNAIL_EXTS = (
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

_SEARCH_LIMIT = 50
PROVIDERS = {
    "soundcloud": f"scsearch{_SEARCH_LIMIT}:",
    "youtube": f"ytsearch{_SEARCH_LIMIT}:",
    "ytmusic": "https://music.youtube.com/search?q=",
    "bilibili": f"bilisearch{_SEARCH_LIMIT}:",
    "nicovideo": f"nicosearch{_SEARCH_LIMIT}:",
    "rokfin": f"rkfnsearch{_SEARCH_LIMIT}:",
    "yahoo": f"yvsearch{_SEARCH_LIMIT}:",
    "googlevideo": f"gvsearch{_SEARCH_LIMIT}:",
    "netverse": f"netsearch{_SEARCH_LIMIT}:",
    "prxstories": f"prxstories{_SEARCH_LIMIT}:",
    "prxseries": f"prxseries{_SEARCH_LIMIT}:",
}

QUALITY = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
_QUALITY_VIDEO = (
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


InfoDict = NewType("InfoDict", dict)


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
class IEBase:
    url: str
    id: str
    extractor: str
    title: str


@dataclass(slots=True)
class IEData(IEBase):
    """yt-dlp InfoDict but more simple and dynamic."""

    creator: str | None = None
    thumbnail_url: str | None = None
    _info_dict: InfoDict | None = None

    @property
    def info_dict(self) -> InfoDict:
        """
        Raises:
            DownloadError: Failed to fetch info data.
        """

        if self._create_info_dict(force_process=False) and self._info_dict:
            info_dict = cast(InfoDict, self._info_dict)
            return info_dict
        else:
            raise DownloadError("Failed to fetch info data.")

    def _create_info_dict(self, force_process=False) -> bool:
        """Fill missed data if not found InfoDict."""

        ydl = YDL(quiet=True)

        if self._info_dict and not force_process:
            return True
        else:
            if info_dict := ydl._get_info_dict(self.url):
                self.creator = info_dict.get("uploader", self.creator)
                self.thumbnail_url = info_dict.get("thumbnail", self.thumbnail_url)
                self._info_dict = info_dict
                return True
            else:
                return False


@dataclass(slots=True)
class IEPlaylist(IEBase):
    total_count: int
    data_list: list[IEData]

    def fetch_data_all(self) -> None:
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            try:
                futures = [
                    pool.submit(item._create_info_dict) for item in self.data_list
                ]
                cf.wait(futures)
            except DownloadError:
                pool.shutdown(wait=False)
                raise


class YDL:
    def __init__(
        self,
        quiet: bool = False,
        logger: Callable | None = None,
        tempdir: Path | None = None,
        outputdir: Path = Path.cwd(),
        ext: str = "mp4",
        ext_quality: int = 9,
    ):
        self.output_path = outputdir
        self.temp_path = tempdir or outputdir

        self.ydl_opts = {
            "paths": {
                "home": str(self.output_path),
                "temp": str(self.temp_path),
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
        self.ydl_opts = self._generate_ydl_opts(ext, ext_quality)

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def _generate_ydl_opts(
        self,
        extension: str,
        quality: int,
    ) -> dict[str, Any]:
        """Generate custom YDLOpts by provided arguments.

        Args:
            extension: Wanted file extension. Custom options will be generated by the extension type.
            quality: Wanted file quality. Range between [0-9].

        Raises:
            ExtTypeError: `extension` is not compatible.
            QualityTypeError: `extension_quality` is out of range.
        """

        if not quality in QUALITY:
            raise QualityTypeError(
                'Failed to determine "quality" range. Expected range between:',
                *QUALITY,
            )

        ydl_opts = self.ydl_opts
        ydl_opts.update({"final_ext": extension})
        ydl_opts["postprocessors"].append(
            {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True}
        )

        if extension in _THUMBNAIL_EXTS:
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
            new_quality = _QUALITY_VIDEO[quality]

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

        return ydl_opts

    def _prepare_filename(self, info: IEData) -> Path:
        ydl_opts = self.ydl_opts

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = info.info_dict
            info_dict["ext"] = ydl_opts["final_ext"]
            filename = ydl.prepare_filename(info_dict)
            return Path(filename)

    def _convert_info_dict(
        self, info_dict: InfoDict, force_process: bool = False
    ) -> IEData | IEPlaylist:
        """Convert raw InfoDict to IEData object

        Args:
            info_dict: Valid InfoDict to parse.
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
                ie._create_info_dict()
                return ie
            else:
                playlist = IEPlaylist(
                    url=info_dict["original_url"],
                    id=info_dict["id"],
                    extractor=info_dict["extractor_key"],
                    title=info_dict["title"],
                    total_count=info_dict["playlist_count"],
                    data_list=ie_list,
                )
                if force_process:
                    playlist.fetch_data_all()
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

    def _get_info_dict(self, query: str, limit: int | None = None) -> InfoDict | None:
        """Fetch InfoDict from valid URL"""

        ydl_opts = self.ydl_opts

        if limit:
            ydl_opts.update({"playlist_items": f"0:{limit}"})

        with YoutubeDL(ydl_opts) as ydl:
            try:
                if info := ydl.extract_info(query, download=False):
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
        """Simple search to get a InfoDict

        Args:
            url: URL to process.

        Returns:
            If the extraction is succesful, return its InfoDict, otherwise return None.
        """

        if info := self._get_info_dict(url):
            return self._convert_info_dict(info, force_process=force_process)
        else:
            return None

    def extract_info_from_search(
        self, query: str, provider: str, limit: int = 5, force_process: bool = False
    ) -> list[IEData] | None:
        """Get one/multiple InfoDict from custom provider like YouTube or SoundCloud.

        Args:
            query: Query to process.
            provider: Provider where do the searchs.
            limit: Max of searchs to do.
        """

        try:
            provider = PROVIDERS[provider]
        except:
            raise ValueError(
                f"{provider} is not a valid provider. Available options:",
                PROVIDERS.keys(),
            )

        if info := self._get_info_dict(f"{provider}{query}", limit=limit):
            data = self._convert_info_dict(info, force_process=force_process)

            if isinstance(data, IEPlaylist):
                return data.data_list
            else:
                return [data]
        else:
            return None

    def convert_info(
        self, query: list[str | list[IEData] | IEData | IEPlaylist]
    ) -> list[IEData]:
        item_list: list[IEData] = []

        for data in query:
            if isinstance(data, str):
                if info := self.extract_info(data):
                    data = info
                else:
                    raise DownloadError(f'Failed to fetch "{data}".')

            match data:
                case IEData():
                    item_list.append(data)
                case IEPlaylist():
                    item_list += data.data_list
                case list():
                    item_list += data
                case _:
                    raise ValueError(
                        f"Must be `str`, `list[IEData]`, `IEData` or `IEPlaylist` object."
                    )
        return item_list

    def download_multiple(
        self, query: str | list[IEData] | IEData | IEPlaylist
    ) -> list[Path]:
        """Simple download without checks"""

        final_downloads: list[Path] = []

        try:
            for item in self.convert_info([query]):
                filename = self.download_single(item, exist_ok=True)
                final_downloads.append(filename)
            return final_downloads
        except DownloadError:
            raise

    def download_single(
        self,
        data: IEData,
        exist_ok: bool = True,
        progress: list[Callable] | bool = True,
    ) -> Path:
        """Download from a IEData object.

        Args:
            data: IEData to download.
            exist_ok: Ignore exception if file exist in output.
            progress: Callable which can get download information.

        Raises:
            DownloadError: yt-dlp throw an error.
            FileExistsError: If exist_ok is False, throw error when the file exist in output.
        """

        ydl_opts = self.ydl_opts

        if isinstance(progress, bool):
            ydl_opts.update({"noprogress": not progress})
        else:
            ydl_opts.update({"progress_hooks": progress, "noprogress": True})

        with YoutubeDL(params=ydl_opts) as ydl:
            temp = Path(self.temp_path / f"{data.extractor} {data.id}")
            temp.parent.mkdir(parents=True, exist_ok=True)

            try:
                filename = self._prepare_filename(data)

                if filename.is_file() and not exist_ok:
                    raise FileExistsError(filename.name)

                info = data.info_dict
                temp.write_text(json.dumps(info))
                ydl.download_with_info_file(temp)
                return filename
            finally:
                temp.unlink(missing_ok=True)
