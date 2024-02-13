from media_dl.types.download import DownloadConfig

from media_dl.downloader import Downloader
from media_dl.types.models import ResultType
from media_dl.extractor import Extractor


class YDL(Extractor):
    def __init__(self) -> None:
        super().__init__()

    def download(
        self,
        data: ResultType,
        config: DownloadConfig | None = None,
        threads: int = 4,
    ) -> None:
        """Download and get the final path from a `Media` item.

        Raises:
            DownloadError: `yt-dlp` related exceptions.
        """

        Downloader(data, config=config, threads=threads).start()
