import concurrent.futures as cf
from pathlib import Path

from loguru import logger
from media_dl.downloader.config import FormatConfig
from media_dl.downloader.pipeline import DownloadPipeline
from media_dl.downloader.state import ProgressCallback
from media_dl.exceptions import DownloadError, OutputTemplateError

from media_dl.models.list import BaseList
from media_dl.models.progress.state import ProgressDownloadCallback
from media_dl.models.stream import LazyStream
from media_dl.types import FILE_FORMAT, StrPath

ExtractResult = BaseList | LazyStream


class StreamDownloader:
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
        """Multi-thread stream downloader.

        If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

        Args:
            format: File format to search or convert with (FFmpeg) if is a extension.
            quality: Quality to filter.
            output: Directory where to save files.
            threads: Maximum processes to execute.
            use_cache: Extract/save stream results from cache.
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
        stream: LazyStream,
        on_progress: ProgressDownloadCallback | None = ProgressCallback(),
    ) -> Path:
        """Single download a `Stream` result.

        Args:
            stream: Target `Stream` to download.
            on_progress: Callback function to get progress information.

        Returns:
            Path to downloaded file.
        """

        pipeline = DownloadPipeline(
            self.config,
            stream,
            cache=self.use_cache,
            on_progress=on_progress,
        )
        return pipeline.run()

    def download_all(
        self,
        data: ExtractResult,
        on_progress: ProgressDownloadCallback | None = ProgressCallback(),
    ) -> list[Path]:
        """Batch download any result.

        Returns:
            List of paths to downloaded files.
        """

        streams = self._data_to_list(data)
        paths: list[Path] = []

        if on_progress:
            on_progress = ProgressCallback()
            on_progress.counter.reset(total=len(streams))
            on_progress.start()

        success = 0
        errors = 0

        with (
            # Temporal workaround
            on_progress,  # type: ignore
            cf.ThreadPoolExecutor(max_workers=self.threads) as executor,
        ):
            futures = {
                executor.submit(self.download, stream, on_progress): stream
                for stream in streams
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
            "{current} of {total} streams completed. {errors} errors.",
            current=success,
            total=len(streams),
            errors=errors,
        )

        return paths

    def _data_to_list(self, data: ExtractResult) -> list[LazyStream]:
        streams = []

        match data:
            case LazyStream():
                streams = [data]
            case BaseList():
                streams = data.streams
            case _:
                raise TypeError(data)

        return streams
