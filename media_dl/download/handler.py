from typing import Literal, Callable
import concurrent.futures as cf
from pathlib import Path
import logging
import shutil
import time

from media_dl.download.worker import FormatWorker
from media_dl.download.progress import ProgressHandler
from media_dl.download.config import FormatConfig, SupportedExtensions
from media_dl.models.format import Format, FormatList
from media_dl.models import ExtractResult, Stream, Playlist
from media_dl.exceptions import MediaError

log = logging.getLogger(__name__)

PROGRESS_STATUS = Literal[
    "downloading",
    "processing",
    "finished",
]
ProgressCallback = Callable[[PROGRESS_STATUS, int, int], None]


class Downloader:
    """Multi-thread downloader."""

    def __init__(
        self,
        config: FormatConfig,
        threads: int = 4,
        render: bool = True,
    ):
        self.config = config
        self.render = render

        self._threads = threads
        self._progress = ProgressHandler(disable=not self.render)

    def download_multiple(self, data: ExtractResult) -> list[Path]:
        log.debug("Download config: %s", self.config.asdict())

        streams = self._prepare_input(data)
        total_streams = len(streams)
        final_paths: list[Path] = []

        log.debug("Founded %s entries.", total_streams)

        with self._progress as progress:
            progress.counter.reset(total_streams)

            with cf.ThreadPoolExecutor(self._threads) as executor:
                futures = [executor.submit(self.download, task) for task in streams]

                success = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        try:
                            final_paths.append(ft.result())
                            success += 1
                        except (cf.CancelledError, MediaError):
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

    def download(
        self,
        stream: Stream,
        format: Format | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        task_id = self._progress.add_task(
            description=stream.display_name, status="Started"
        )
        config = self.config

        # Create output directory
        output = Path(config.output)
        output.mkdir(parents=True, exist_ok=True)

        try:
            # Resolve stream
            if not stream.formats:
                stream = stream.update()
                self._progress.update(task_id, description=stream.display_name)

            filename = stream.display_name

            # If is duplicated will stop.
            if path := self._check_file_duplicate(filename):
                self._progress.update(
                    task_id, status="Skipped", completed=100, total=100
                )

                log.info(
                    'Skipped: "%s" (File already exists as "%s").',
                    stream.display_name,
                    path.suffix[1:],
                )
                return path

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

                format = self._extract_best_format(stream.formats, config)

                if not config.convert and config.type != format.type:
                    log.debug(
                        'Format "%s" and config "%s" missmatch in "%s". Config changed to "%s".',
                        format.type,
                        config.type,
                        stream.display_name,
                        format.type,
                    )
                    config.format = format.type

            # STATUS: Download
            self._progress.update(task_id, status="Downloading")

            callbacks = [
                lambda completed, total: self._progress.update(
                    task_id, completed=completed, total=total
                )
            ]
            (
                callbacks.append(
                    lambda completed, total: on_progress(
                        "downloading", completed, total
                    )
                )
                if on_progress
                else None
            )

            # Run download
            worker = FormatWorker(format=format, on_progress=callbacks)
            filepath = worker.start()

            # STATUS: Postprocessing
            if config.convert:
                status = "Converting"
            else:
                status = "Processing"

            self._progress.update(task_id, status=status)
            (
                on_progress("processing", worker._downloaded, worker._total_filesize)
                if on_progress
                else None
            )
            log.debug('Postprocessing "%s"', stream.display_name)

            # Run postprocessing
            filepath = config._run_postproces(filepath, stream._extra_info)
            filename = filename + filepath.suffix

            # Move file
            filepath = filepath.rename(filepath.parent / filename)
            filepath = shutil.move(filepath, output / filename)

            # STATUS: Finish
            self._progress.update(task_id, status="Finished")
            (
                on_progress("finished", worker._downloaded, worker._total_filesize)
                if on_progress
                else None
            )
            log.info('Finished: "%s".', stream.display_name)

            return filepath
        except MediaError as err:
            error_name = err.__class__.__name__

            log.error('Failed to download "%s".', stream.display_name)
            log.error("%s: %s", error_name, str(err))

            self._progress.update(task_id, status="Error")
            raise
        finally:
            self._progress.counter.advance()
            time.sleep(1.0)
            self._progress.remove_task(task_id)

    def _extract_best_format(
        self, format_list: FormatList, custom_config: FormatConfig | None = None
    ) -> Format:
        """Extract best format in stream formats."""

        config = custom_config if custom_config else self.config

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

        log.info('🔎 Founded %s: "%s".', type, query)
        return streams

    def _check_file_duplicate(self, filename: str) -> Path | None:
        output = Path(self.config.output)
        matches = list(output.glob(filename + ".*"))

        if extension := self.config.convert:
            path = [path for path in matches if path.suffix[1:] == extension]
        else:
            path = [
                path
                for path in matches
                if path.stem == filename
                and path.suffix[1:] in SupportedExtensions.audio
            ]

        return path[0] if path else None
