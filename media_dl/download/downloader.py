import concurrent.futures as cf
from threading import Event
import logging

from media_dl.download.progress import ProgressHandler, ProgressTask
from media_dl.download.format_download import FormatDownloader, DownloaderError
from media_dl.download.format_config import FormatConfig, FILE_REQUEST

from media_dl.models import ExtractResult, Stream, StreamList, Playlist
from media_dl.models.format import Format, FormatList

log = logging.getLogger(__name__)


class Downloader:
    """Multi-thread downloader interface."""

    def __init__(
        self,
        format: FILE_REQUEST,
        quality: int | None = None,
        max_threads: int = 4,
        error_limit: int = 4,
        render_progress: bool = True,
        **config,
    ):
        self.render = render_progress

        self.quality = quality
        self.config = FormatConfig(format=format, **config)

        if not self.config.is_ffmpeg_installed():
            log.warning(
                "FFmpeg is not installed. File conversion and metadata embeding will be disabled."
            )

        self._progress = ProgressHandler(disable=not self.render)
        self._threads = max_threads
        self._error_limit = error_limit
        self._event = Event()

    def download(self, data: ExtractResult | Format) -> None:
        """Start download and process the files with provided format parameters."""

        log.debug("Downloading with config: %s", self.config.asdict())
        log.debug("FFmpeg support: %s", self.config.is_ffmpeg_installed())

        with self._progress:
            streams = self._prepare_input(data)
            self._process_formats(streams)

    def _prepare_input(self, data: ExtractResult | Format) -> list[Stream]:
        match data:
            case Format():
                log.info("Format %s", data.url)
                return [Stream.from_format(data)]
            case Stream():
                log.info("Stream: '%s'", data.display_name)
                return [data]
            case list():
                return data
            case Playlist():
                log.info("Playlist: '%s'", data.title)
                return data.streams
            case _:
                raise TypeError(data)

    def _process_formats(self, data: list[Stream]) -> None:
        total_entries = len(data)

        self._progress.counter.set_total(total_entries)

        log.debug("Founded %s entries", total_entries)

        with cf.ThreadPoolExecutor(self._threads) as executor:
            futures = [executor.submit(self._download_thread, task) for task in data]

            is_single = True if total_entries == 1 else False

            try:
                errors = 0

                for ft in cf.as_completed(futures):
                    result = ft.result()

                    if not result:
                        errors += 1

                    if is_single and errors >= 1:
                        raise DownloaderError("Download failed.")
                    elif errors > self._error_limit:
                        raise DownloaderError(
                            "Too many errors to continue downloading the playlist."
                        )
            except DownloaderError as err:
                log.error("\n" + str(err))
                raise
            finally:
                self._event.set()
                cf.wait(futures)
                self._event.clear()

    def _download_thread(self, stream: Stream) -> bool:
        if self._event.is_set():
            return False

        log.debug("Resolving %s", stream.url)

        stream, format, progress = self._prepare_stream(stream)

        log.debug(
            "Downloading '%s' with format '%s (%s)'",
            stream.display_name,
            format.extension,
            format.display_quality,
        )

        try:
            FormatDownloader(
                format,
                config=self.config,
                on_progress=progress.ydl_progress_hook,
                event=self._event,
            ).start()
        except DownloaderError as err:
            log.error("Failed to download '%s'", stream.display_name)
            log.error("YDL-Error: %s", str(err))
            return False
        else:
            log.info("Finished '%s'", stream.display_name)
            return True

    def _prepare_stream(self, stream: Stream) -> tuple[Stream, Format, ProgressTask]:
        progress = self._progress.create_task(stream.display_name)

        # Check if empty
        if not stream.formats:
            stream = stream.get_updated()
            progress.message = stream.display_name
            progress.update()

        format = self._get_best_format(stream.formats)

        return stream, format, progress

    def _get_best_format(self, fmt_list: FormatList) -> Format:
        conf = self.config

        # Filter by extension
        if f := conf.target_convert and fmt_list.filter(extension=conf.target_convert):
            final = f
        # Filter by type
        elif f := fmt_list.filter(type=conf.target_type):
            final = f
        # Filter fallback to available type.
        elif f := fmt_list.filter(type="video") or fmt_list.filter(type="only-audio"):
            final = f
        else:
            raise TypeError("Not matches founded when filter the format list.")

        if self.quality:
            return f.get_closest_quality(self.quality)
        else:
            return final[-1]
