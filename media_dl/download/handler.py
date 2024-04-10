import concurrent.futures as cf
from pathlib import Path
import logging
import shutil
import time

from media_dl.download.progress import ProgressHandler
from media_dl.download.worker import FormatWorker, DownloadError
from media_dl.download.config import FormatConfig, SupportedExtensions

from media_dl.extractor import ExtractionError
from media_dl.models.format import Format, FormatList
from media_dl.models import ExtractResult, Stream, Playlist

log = logging.getLogger(__name__)


def progress_hook(progress: ProgressHandler, task_id, status, completed, total):
    match status:
        case "error":
            status = "Error"
        case "downloading":
            status = "Downloading"
        case "finished":
            status = "Download Finished"

            if completed == 0:
                completed = 100
                total = 100

    progress.update(task_id, status=status, completed=completed, total=total)


class Downloader:
    """Multi-thread downloader interface."""

    def __init__(
        self,
        format_config: FormatConfig,
        max_threads: int = 4,
        render_progress: bool = True,
    ):
        self.config = format_config
        self.render = render_progress

        self._progress = ProgressHandler(disable=not self.render)
        self._threads = max_threads

    def download_multiple(self, data: ExtractResult):
        log.debug("Downloading with config: %s", self.config.asdict())

        streams = self._prepare_input(data)
        total_streams = len(streams)
        final_paths: list[Path] = []

        log.debug("Founded %s entries.", total_streams)

        with self._progress as progress:
            progress.counter.set_total(total_streams)

            with cf.ThreadPoolExecutor(self._threads) as executor:
                futures = [
                    executor.submit(self._download_worker, task) for task in streams
                ]

                success = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        try:
                            final_paths.append(ft.result())
                            success += 1
                        except (cf.CancelledError, DownloadError):
                            errors += 1
                            log.debug("%s Errors catched.", errors)
                except KeyboardInterrupt:
                    log.warning(
                        "❗ Canceling downloads... (press Ctrl+C again to force)"
                    )
                    raise
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

                    log.debug(f"{success} of {total_streams} streams downloaded.")

        return final_paths

    def download_single(self, stream: Stream, format: Format | None = None) -> Path:
        with self._progress as progress:
            progress.counter.set_total(1)

            path = self._download_worker(stream, format)

            return path

    @staticmethod
    def extract_best_format(format_list: FormatList, config: FormatConfig) -> Format:
        """Resolve and extract the best format in the instance."""

        # Filter by extension
        if f := config.convert and format_list.filter(extension=config.convert):
            final = f
        # Filter by type
        elif f := format_list.filter(type=config.type):
            final = f
        # Filter fallback to available type.
        elif f := format_list.filter(type="video") or format_list.filter(type="audio"):
            final = f
        else:
            raise TypeError("Not matches founded in format list.")

        if config.quality:
            return f.get_closest_quality(config.quality)
        else:
            return final[-1]

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

        log.info('🔎 Founded %s: "%s".\n', type, query)
        return streams

    def _download_worker(self, stream: Stream, format: Format | None = None) -> Path:
        task_id = self._progress.add_task(
            description=stream.display_name, status="Started"
        )
        config = self.config

        try:
            # Resolve stream
            if not stream.formats:
                stream = stream.update()
                self._progress.update(task_id, description=stream.display_name)
            else:
                stream = stream

            # Create output directory
            output = Path(config.output)
            output.mkdir(parents=True, exist_ok=True)
            filename = stream.display_name

            # Resolve duplicates
            matches = list(output.glob(filename + ".*"))

            if (
                p := matches
                and config.convert
                and [path for path in matches if path.suffix[1:] == config.convert]
                or not config.convert
                and [
                    path
                    for path in matches
                    if path.stem == filename
                    and path.suffix[1:] in SupportedExtensions.audio
                ]
            ):
                p = p[0]

                self._progress.update(
                    task_id, status="Skipped", completed=100, total=100
                )

                log.info(
                    '[Skipped]: "%s" (File already exists as "%s").',
                    stream.display_name,
                    p.suffix[1:],
                )
                return p

            # Resolve format
            if format:
                if not format in stream.formats:
                    raise ValueError(f"'{format.id}' format id not founded in Stream.")

                if not config.convert:
                    config.format = format.type
            else:
                if (
                    not config.convert
                    and config.format == "video"
                    and stream._is_music_site()
                ):
                    log.debug(
                        'Detected music site in "%s". Config changed to "audio".',
                        stream.display_name,
                    )
                    config.format = "audio"

                format = self.extract_best_format(stream.formats, config)

                if not config.convert and config.type != format.type:
                    log.debug(
                        'Format "%s" and config "%s" missmatch in "%s". Config changed to "%s".',
                        format.type,
                        config.type,
                        stream.display_name,
                        format.type,
                    )
                    config.format = format.type

            # Start download
            filepath = FormatWorker(
                format=format,
                on_progress=lambda *args: progress_hook(self._progress, task_id, *args),
            ).start()

            # Postprocessing
            if config.convert:
                status = "Converting"
            else:
                status = "Processing"

            log.debug('Postprocessing "%s"', stream.display_name)
            self._progress.update(task_id, status=status)

            filepath = config.run_postproces(filepath, stream._extra_info)
            filename = filename + filepath.suffix

            # Move file
            filepath = filepath.rename(filepath.parent / filename)
            filepath = shutil.move(filepath, output / filename)

            # Finish
            self._progress.update(task_id, status="Finished")

            log.info('[Finished]: "%s".', stream.display_name)
            return filepath
        except (DownloadError, ExtractionError) as err:
            error_name = err.__class__.__name__

            log.error('Failed to download "%s".', stream.display_name)
            log.error("%s: %s", error_name, str(err))

            self._progress.update(task_id, status="Error")
            raise
        finally:
            self._progress.counter.advance()
            time.sleep(1.0)
            self._progress.remove_task(task_id)
