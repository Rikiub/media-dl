from media_dl.extractor import Extractor
from media_dl.downloader import Downloader
from media_dl.types.download import DownloadConfig


class YDL(Extractor, Downloader):
    def __init__(
        self,
        config: DownloadConfig | None = None,
        threads: int = 4,
    ):
        Extractor.__init__(self)
        Downloader.__init__(self, config=config, max_threads=threads)
