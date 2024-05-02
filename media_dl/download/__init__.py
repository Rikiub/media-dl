from typing import Literal, Callable
import concurrent.futures as cf
from pathlib import Path
from os import PathLike
import logging
import shutil
import time

from media_dl.exceptions import MediaError
from media_dl._ydl import (
    SupportedExtensions,
    run_postproces,
    download_thumbnail,
    download_subtitle,
)
from media_dl.models import ExtractResult, Stream, Playlist
from media_dl.models.format import Format, FormatList

from media_dl.download.config import FormatConfig, FILE_REQUEST
from media_dl.download.worker import DownloadFormat
from media_dl.download.progress import DownloadProgress


log = logging.getLogger(__name__)

PROGRESS_STATUS = Literal[
    "downloading",
    "processing",
    "finished",
]
ProgressCallback = Callable[[PROGRESS_STATUS, int, int], None]

StrPath = str | PathLike[str]


class Downloader:
    """Multi-thread stream downloader.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: File format to search or convert if is a extension.
        quality: Quality to filter.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)

    Raises:
        FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
    """

    def __init__(
        self,
        format: FILE_REQUEST = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        ffmpeg: StrPath | None = None,
        metadata: bool = True,
        threads: int = 4,
        render_progress: bool = False,
    ):
        self.config = FormatConfig(
            format=format,
            quality=quality,
            output=Path(output),
            ffmpeg=Path(ffmpeg) if ffmpeg else None,
            metadata=metadata,
        )
        self.render_progress = render_progress
        self.threads = threads

        self._progress = DownloadProgress(disable=self.render_progress)

    def __enter__(self):
        self.start_progress()
        return self

    def __exit__(self, a, b, c):
        self.stop_progress()

    def start_progress(self):
        self._progress.start()

    def stop_progress(self):
        self._progress.stop()

    def download_all(self, media: ExtractResult) -> list[Path]:
        """Download any result.

        Returns:
            List of paths to downloaded files.

        Raises:
            MediaError: Something bad happens when download.
        """

        log.debug("Download config: %s", self.config.asdict())

        streams = self._media_to_list(media)
        total_streams = len(streams)
        final_paths: list[Path] = []

        log.debug("Founded %s entries.", total_streams)
        self._progress.counter.reset(total_streams)

        with cf.ThreadPoolExecutor(self.threads) as executor:
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
                log.warning("❗ Canceling downloads... (press Ctrl+C again to force)")
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
        """Download a single `Stream` result.

        Args:
            stream: Target `Stream` to download.
            format: Specific `Stream` format to download. By default will select BEST format.
            on_progress: Callback function to get download progress information.

        Returns:
            Path to downloaded file.

        Raises:
            MediaError: Something bad happens when download.
            ValueError: Provided `Format` wasn't founded in `Stream`.
        """

        task_id = self._progress.add_task(
            description=stream.display_name, status="Started"
        )

        config = self.config
        config.output.mkdir(parents=True, exist_ok=True)

        try:
            # Resolve stream
            if not stream.formats:
                stream = stream.update()

            filename = stream.display_name
            self._progress.update(task_id, description=stream.display_name)

            # Stop if duplicate.
            if path := self._check_file_duplicate(filename):
                self._progress.update(
                    task_id, status="Skipped", completed=100, total=100
                )
                if on_progress:
                    on_progress("finished", 0, 0)

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
                if not config.convert and stream._is_music_site():
                    log.debug(
                        '"%s" is from a music site. Change config to "audio".',
                        stream.display_name,
                    )
                    config.format = "audio"

                format = self._extract_best_format(stream.formats, config)

                if not config.convert and config.type != format.type:
                    log.debug(
                        'Format "%s" and config "%s" missmatch in "%s". Change config to "%s".',
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
            if on_progress:
                callbacks.append(
                    lambda completed, total: on_progress(
                        "downloading", completed, total
                    )
                )

            # Run download
            log.debug(
                'Downloading "%s" with format: %s (%s %s) (%s)',
                stream.display_name,
                format.id,
                format.extension,
                format.display_quality,
                format.type,
            )

            worker = DownloadFormat(format=format, callbacks=callbacks)
            filepath = worker.start()

            # STATUS: Postprocessing
            log.debug('Postprocessing "%s"', stream.display_name)
            self._progress.update(task_id, status="Processing")
            if on_progress:
                on_progress(
                    "processing", worker._total_filesize, worker._total_filesize
                )

            # Download resources
            download_thumbnail(filename, stream._extra_info)
            download_subtitle(filename, stream._extra_info)

            # Run postprocessing
            filepath = run_postproces(filepath, stream._extra_info, config._gen_opts())
            filename = filename + filepath.suffix

            # Move file
            filepath = filepath.rename(filepath.parent / filename)
            filepath = shutil.move(filepath, config.output / filename)

            # STATUS: Finish
            log.info('Finished: "%s".', stream.display_name)
            self._progress.update(task_id, status="Finished")
            if on_progress:
                on_progress("finished", worker._total_filesize, worker._total_filesize)

            return filepath
        except MediaError as err:
            log.error('Failed to download "%s": %s', stream.display_name, str(err))
            self._progress.update(task_id, status="Error")
            raise
        finally:
            self._progress.counter.advance()
            time.sleep(1.0)
            self._progress.remove_task(task_id)

    def _media_to_list(self, media: ExtractResult) -> list[Stream]:
        match media:
            case Stream():
                streams = [media]
            case Playlist():
                streams = media.streams
            case list():
                streams = media
            case _:
                raise TypeError(media)

        return streams

    def _extract_best_format(
        self, formats: FormatList, custom_config: FormatConfig | None = None
    ) -> Format:
        """Extract best format in stream formats."""

        config = custom_config if custom_config else self.config

        # Filter by extension
        if f := config.convert and formats.filter(extension=config.convert):
            final = f
        # Filter by type
        elif f := formats.filter(type=config.type):
            final = f
        # Filter fallback to available type.
        elif f := formats.filter(type="video") or formats.filter(type="audio"):
            final = f
        else:
            raise TypeError("Not matches founded in format list.")

        if config.quality:
            return f.get_closest_quality(config.quality)
        else:
            return final[-1]

    def _check_file_duplicate(self, filename: str) -> Path | None:
        """Check if file is duplicated in output directory.

        Returns:
            Path to duplicated file, if not exist, return None.
        """

        matches = list(self.config.output.glob(filename + ".*"))

        if extension := self.config.convert:
            paths = [path for path in matches if path.suffix[1:] == extension]
        else:
            paths = [
                path
                for path in matches
                if path.stem == filename
                and path.suffix[1:] in SupportedExtensions.video
                or path.suffix[1:] in SupportedExtensions.audio
            ]

        return paths[0] if paths else None
