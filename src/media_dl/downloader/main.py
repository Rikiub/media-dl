import concurrent.futures as cf
from pathlib import Path

from loguru import logger

from media_dl.downloader.config import FormatConfig
from media_dl.downloader.pipeline import DownloadPipeline
from media_dl.downloader.states.progress import ProgressCallback
from media_dl.exceptions import DownloadError, OutputTemplateError
from media_dl.models.content.list import MediaList
from media_dl.models.content.media import LazyMedia
from media_dl.models.content.types import ExtractResult, MediaListEntries
from media_dl.models.progress.media import MediaDownloadCallback
from media_dl.types import FILE_FORMAT, StrPath

_MediaResult = ExtractResult | MediaListEntries
MediaResult = MediaList | _MediaResult | list[LazyMedia]


class MediaDownloader:
    def __init__(
        self,
        format: FILE_FORMAT = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        threads: int = 4,
        use_cache: bool = True,
        ffmpeg_path: StrPath | None = None,
        embed_metadata: bool = True,
    ):
        """Multi-thread media downloader.

        If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

        Args:
            format: File format to search or convert with (FFmpeg) if is a extension.
            quality: Quality to filter.
            output: Directory where to save files.
            threads: Maximum processes to execute.
            use_cache: Extract/save media results from cache.
            ffmpeg_path: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
            embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
            show_progress: Choice if render download progress.

        Raises:
            FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
        """

        self.config = FormatConfig(
            format=format,
            quality=quality,
            output=Path(output),
            ffmpeg_path=Path(ffmpeg_path) if ffmpeg_path else None,
            embed_metadata=embed_metadata,
        )
        self.threads = threads
        self.use_cache = use_cache

    def download(
        self,
        media: LazyMedia,
        on_progress: MediaDownloadCallback | None = ProgressCallback(),
    ) -> Path:
        """Single download a `Media` result.

        Args:
            media: Target `Media` to download.
            on_progress: Callback function to get progress information.

        Returns:
            Path to downloaded file.
        """

        pipeline = DownloadPipeline(
            self.config,
            media,
            cache=self.use_cache,
            on_progress=on_progress,
        )
        return pipeline.run()

    def download_all(
        self,
        data: MediaResult,
        on_progress: MediaDownloadCallback | None = ProgressCallback(),
    ) -> list[Path]:
        """Batch download any result.

        Returns:
            List of paths to downloaded files.
        """

        medias = self._data_to_list(data)
        paths: list[Path] = []

        if on_progress:
            on_progress = ProgressCallback()
            on_progress.counter.reset(total=len(medias))
            on_progress.start()

        success = 0
        errors = 0

        with (
            # Temporal workaround
            on_progress,  # type: ignore
            cf.ThreadPoolExecutor(max_workers=self.threads) as executor,
        ):
            futures = {
                executor.submit(self.download, media, on_progress): media
                for media in medias
            }

            try:
                for future in cf.as_completed(futures):
                    try:
                        paths.append(future.result())
                        success += 1
                    except (ConnectionError, DownloadError) as e:
                        logger.error(f"Failed to download: {e}")
                        errors += 1
                    except OutputTemplateError as e:
                        logger.error(str(e).strip('"'))
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise SystemExit()
            except KeyboardInterrupt:
                logger.warning(
                    "❗ Canceling downloads... (press Ctrl+C again to force)"
                )
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        logger.debug(
            "{current} of {total} medias completed. {errors} errors.",
            current=success,
            total=len(medias),
            errors=errors,
        )

        return paths

    def _data_to_list(self, data: MediaResult) -> list[LazyMedia]:
        medias = []

        match data:
            case LazyMedia():
                medias = [data]
            case MediaList():
                medias = data.medias
            case list():
                return data  # type: ignore
            case _:
                raise TypeError("Unable to unpack media list.")

        return medias
