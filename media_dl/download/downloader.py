import concurrent.futures as cf
from pathlib import Path
import logging

from media_dl.helper import MUSIC_SITES
from media_dl.download.progress import ProgressHandler
from media_dl.download.format_download import FormatDownloader, DownloaderError
from media_dl.download.format_config import FormatConfig

from media_dl.models import ExtractResult, Stream, Playlist, Format
from media_dl.models.format import Format, FormatList

log = logging.getLogger(__name__)

DEFAULT_TEMPLATE = "%(uploader)s - %(title)s"


class Downloader:
    """Multi-thread downloader interface."""

    def __init__(
        self,
        format_config: FormatConfig,
        quality: int | None = None,
        max_threads: int = 4,
        error_limit: int = 4,
        render_progress: bool = True,
    ):
        self.render = render_progress

        self.quality = quality
        self.config = format_config

        self._progress = ProgressHandler(disable=not self.render)
        self._threads = max_threads
        self._error_limit = error_limit

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
                futures = [
                    executor.submit(self._download_task, task) for task in streams
                ]

                success = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        try:
                            paths.append(ft.result())
                            success += 1
                        except (cf.CancelledError, DownloaderError):
                            log.debug("%s Errors catched", errors)
                            errors += 1

                        if errors >= error_limit:
                            msg = (
                                "Download failed"
                                if is_single
                                else "Too many errors to continue downloading the playlist."
                            )
                            raise DownloaderError(msg)
                except KeyboardInterrupt:
                    log.warning(
                        "❗ Canceling downloads... (press Ctrl+C again to force)"
                    )
                    raise
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

                    log.debug(f"❗ {success} of {total} streams downloaded.")
        return paths

    def download(self, stream: Stream, format: Format | None = None) -> Path:
        with self._progress as prog:
            prog.counter.set_total(1)
            return self._download_task(stream, format)

    def _download_task(self, stream: Stream, format: Format | None = None) -> Path:
        progress = self._progress.create_task(stream.display_name)

        # Resolve Format
        if not stream.formats:
            stream = stream.update()
            progress.message = stream.display_name
            progress.update()

        config = self.config

        # Change config if stream URL is a music site.
        if not config.convert:
            for site in MUSIC_SITES:
                if site in stream.url:
                    config.format = "audio"
                    break

        if format:
            if not format in stream.formats:
                raise ValueError(f"'{format.id}' Format ID not founded in Stream.")

            format = format
        else:
            format = self._get_best_format(stream.formats, config)

        # Start Download
        log.debug(
            "Downloading '%s' with format %s (%s %s)",
            stream.display_name,
            format.id,
            format.extension,
            format.display_quality,
        )

        try:
            path = FormatDownloader(
                format=format,
                meta_stream=stream,
                config=config,
                on_progress=progress.ydl_progress_hook,
            ).start()
        except DownloaderError as err:
            log.error("Failed to download '%s'", stream.display_name)
            log.error("%s: %s", err.__class__.__name__, str(err))
            raise

        log.info("Finished '%s'", stream.display_name)
        return path

    def _prepare_input(self, data: ExtractResult) -> list[Stream]:
        match data:
            case Stream():
                type = "Stream"
                query = data.display_name
                result = [data]
            case Playlist():
                type = "Playlist"
                query = data.title
                result = data.streams
            case list():
                type = "Stream List"
                query = ""
                result = data
            case _:
                raise TypeError(data)

        log.info("🔎 Founded %s: '%s'", type, query)
        return result

    def _get_best_format(
        self,
        format_list: FormatList,
        custom_config: FormatConfig | None = None,
    ) -> Format:
        conf = custom_config if custom_config else self.config

        # Filter by extension
        if f := conf.convert and format_list.filter(extension=conf.convert):
            final = f
        # Filter by type
        elif f := format_list.filter(type=conf.type):
            final = f
        # Filter fallback to available type.
        elif f := format_list.filter(type="video") or format_list.filter(type="audio"):
            final = f
        else:
            raise TypeError("Not matches founded in format list.")

        if self.quality:
            return f.get_closest_quality(self.quality)
        else:
            return final[-1]
