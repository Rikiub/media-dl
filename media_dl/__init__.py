from media_dl.downloader.progress import DownloaderProgress, FormatConfig
from media_dl.extractor import Extractor


class YDL(Extractor, DownloaderProgress):
    def __init__(
        self,
        config: FormatConfig | None = None,
        threads: int = 4,
        quiet: bool = False,
    ):
        Extractor.__init__(self)
        DownloaderProgress.__init__(
            self,
            config=config,
            max_threads=threads,
            render=not quiet,
        )
