import concurrent.futures as cf
from pathlib import Path
import logging

from media_dl.download.progress import ProgressHandler
from media_dl.download.worker import DownloadWorker, DownloadError
from media_dl.download.config import FormatConfig

from media_dl.extractor import ExtractionError
from media_dl.models import ExtractResult, Stream, Playlist, Format
from media_dl.models.format import Format

log = logging.getLogger(__name__)


class Downloader:
    """Multi-thread downloader interface."""

    def __init__(
        self,
        format_config: FormatConfig,
        max_threads: int = 4,
        error_limit: int = 4,
        render_progress: bool = True,
    ):
        self.config = format_config
        self.render = render_progress

        self._progress = ProgressHandler(disable=not self.render)
        self._threads = max_threads
        self._error_limit = error_limit

    def _prepare_input(self, data: ExtractResult) -> list[Stream]:
        match data:
            case Stream():
                type = "Stream"
                query = data.display_name
                streams = [data]
            case Playlist():
                type = "Playlist"
                query = data.title
                streams = data.streams
            case list():
                type = "Stream List"
                query = ""
                streams = data
            case _:
                raise TypeError(data)

        log.info("🔎 Founded %s: '%s'", type, query)
        return streams

    def download_multiple(self, data: ExtractResult):
        log.debug("Downloading with config: %s", self.config.asdict())

        streams = self._prepare_input(data)

        total = len(streams)
        is_single = True if total == 1 else False
        error_limit = 1 if is_single else self._error_limit

        paths: list[Path] = []

        log.debug("Founded %s entries", total)

        with self._progress as prog:
            prog.counter.set_total(total)

            with cf.ThreadPoolExecutor(self._threads) as executor:
                futures = [executor.submit(self._dl_worker, task) for task in streams]

                success = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        try:
                            paths.append(ft.result())
                            success += 1
                        except (cf.CancelledError, DownloadError):
                            errors += 1
                            log.debug("%s Errors catched", errors)

                        if errors >= error_limit:
                            msg = (
                                "Download failed"
                                if is_single
                                else "Too many errors to continue downloading the playlist."
                            )
                            raise DownloadError(msg)
                except KeyboardInterrupt:
                    log.warning(
                        "❗ Canceling downloads... (press Ctrl+C again to force)"
                    )
                    raise
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

                    log.debug(f"{success} of {total} streams downloaded.")
        return paths

    def download_single(self, stream: Stream, format: Format | None = None) -> Path:
        with self._progress as prog:
            prog.counter.set_total(1)
            return self._dl_worker(stream, format)

    def _dl_worker(self, stream: Stream, format: Format | None = None) -> Path:
        progress = self._progress.create_task(stream.display_name)

        # Resolve Format
        if not stream.formats:
            stream = stream.update()
            progress.message = stream.display_name
            progress.update()

        try:
            path = DownloadWorker(
                stream=stream,
                format=format,
                config=self.config,
                on_progress=progress.ydl_progress_hook,
            ).start()
        except (DownloadError, ExtractionError) as err:
            log.error("Failed to download '%s'", stream.display_name)
            log.error("%s: %s", err.__class__.__name__, str(err))
            raise

        log.info("Finished '%s'", stream.display_name)
        return path
