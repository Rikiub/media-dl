import concurrent.futures as cf
from threading import Event
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
        self._event = Event()

    def download_multiple(self, data: ExtractResult):
        log.debug("Downloading with config: %s", self.config.asdict())

        streams = self._prepare_input(data)
        total = len(streams)
        is_single = True if total == 1 else False

        paths: list[Path] = []

        log.debug("Founded %s entries", total)

        with self._progress:
            self._progress.counter.set_total(total)

            with cf.ThreadPoolExecutor(self._threads) as executor:
                futures = [executor.submit(self.download, task) for task in streams]

                try:
                    errors = 0

                    for ft in cf.as_completed(futures):
                        try:
                            paths.append(ft.result())
                        except:
                            errors += 1

                        if is_single and errors >= 1:
                            raise DownloaderError("Download failed.")
                        elif errors > self._error_limit:
                            raise DownloaderError(
                                "Too many errors to continue downloading the playlist."
                            )
                finally:
                    self._event.set()
                    cf.wait(futures)
                    self._event.clear()

        return paths

    def download(self, stream: Stream, format: Format | None = None) -> Path:
        with self._progress:
            if self._event.is_set():
                raise cf.CancelledError()

            progress = self._progress.create_task(stream.display_name)

            # Resolve Format
            if not stream.formats:
                stream = stream.update()
                progress.message = stream.display_name
                progress.update()

            config = self.config

            # Change config is stream URL is a music site.
            if not config.convert:
                for site in MUSIC_SITES:
                    if site in stream.url:
                        log.debug(
                            "%s is a music site. Changing config to 'audio'", stream.url
                        )
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
                    event=self._event,
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
