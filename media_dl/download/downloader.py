import concurrent.futures as cf
import logging
import shutil
import time
from pathlib import Path
from typing import Callable, Literal

from media_dl._ydl import (
    download_subtitles,
    download_thumbnail,
    parse_name_template,
    run_postproces,
)
from media_dl.download import worker
from media_dl.download.config import FILE_FORMAT, FormatConfig
from media_dl.exceptions import MediaError
from media_dl.models.format import Format, FormatList
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStreams, Stream
from media_dl.path import StrPath, get_tempfile
from media_dl.rich import DownloadProgress

log = logging.getLogger(__name__)

PROGRESS_STATUS = Literal[
    "downloading",
    "processing",
    "finished",
]
ProgressCallback = Callable[[PROGRESS_STATUS, int, int], None]

ExtractResult = Playlist | LazyStreams | Stream


class Downloader:
    """Multi-thread stream downloader.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: File format to search or convert if is a extension.
        quality: Quality to filter.
        output: Directory where to save files.
        ffmpeg: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
        threads: Maximum processes to execute.
        show_progress: Choice if render download progress.

    Raises:
        FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
    """

    def __init__(
        self,
        format: FILE_FORMAT = "video",
        quality: int | None = None,
        output: StrPath = Path.cwd(),
        ffmpeg: StrPath | None = None,
        metadata: bool = True,
        threads: int = 4,
        show_progress: bool = True,
    ):
        self.config = FormatConfig(
            format=format,
            quality=quality,
            output=Path(output),
            ffmpeg=Path(ffmpeg) if ffmpeg else None,
            metadata=metadata,
        )
        self._threads = threads
        self._progress = DownloadProgress(disable=not show_progress)

        log.debug("Download config: %s", self.config.to_dict())

    def download_all(self, media: ExtractResult) -> list[Path]:
        """Download any result.

        Returns:
            List of paths to downloaded files.

        Raises:
            MediaError: Something bad happens when download.
        """

        streams = self._media_to_list(media)
        paths: list[Path] = []

        log.debug("Founded %s entries.", len(streams))
        self._progress.counter.reset(len(streams))

        with self._progress:
            with cf.ThreadPoolExecutor(max_workers=self._threads) as executor:
                futures = [
                    executor.submit(self._download_work, task) for task in streams
                ]

                success = 0
                errors = 0

                try:
                    for ft in cf.as_completed(futures):
                        try:
                            paths.append(ft.result())
                            success += 1
                        except MediaError:
                            errors += 1
                except (cf.CancelledError, KeyboardInterrupt):
                    log.warning(
                        "❗ Canceling downloads... (press Ctrl+C again to force)"
                    )
                    raise KeyboardInterrupt()
                finally:
                    executor.shutdown(wait=True, cancel_futures=True)

                    log.debug(
                        "%s of %s streams completed. %s errors.",
                        success,
                        len(streams),
                        errors,
                    )
        return paths

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

        with self._progress:
            self._progress.counter.reset(total=1)
            return self._download_work(stream, format, on_progress)

    def _download_work(
        self,
        stream: Stream,
        format: Format | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        task_id = self._progress.add_task(
            description=stream.display_name, status="Started"
        )

        try:
            # Resolve stream
            if stream.has_missing_info():
                stream = stream.get_updated()
                self._progress.update(task_id, description=stream.display_name)

            log.debug('"%s": Downloading stream.', stream.id)

            format, download_config = self._resolve_format(stream, format)

            # STATUS: Download
            self._progress.update(task_id, status="Downloading")
            log.debug(
                '"%s": Download format "%s" (%s %s) (%s).',
                stream.id,
                format.id,
                format.extension,
                format.display_quality,
                format.type,
            )

            # Configure callbacks
            total_filesize: int = 0

            def update_filesize(filesize: int):
                nonlocal total_filesize
                total_filesize = filesize

            callbacks = [
                lambda _, filesize: update_filesize(filesize),
                lambda completed, total: self._progress.update(
                    task_id, completed=completed, total=total
                ),
            ]
            if on_progress:
                callbacks.append(
                    lambda completed, total: on_progress(
                        "downloading", completed, total
                    )
                )

            # Run download
            downloaded_file = worker.download(
                filepath=get_tempfile(),
                format=format,
                callbacks=callbacks,
            )

            # STATUS: Postprocess
            if on_progress:
                on_progress("processing", total_filesize, total_filesize)
            self._progress.update(task_id, status="Processing")
            log.debug('"%s": Postprocessing downloaded file.', stream.id)

            # Final filename
            output_name = parse_name_template(
                stream._extra_info, "%(uploader)s - %(title)s"
            )

            # Download resources
            if download_thumbnail(output_name, stream._extra_info):
                log.debug('"%s": Thumbnail founded.', stream.id)
            if download_subtitles(output_name, stream._extra_info):
                log.debug('"%s": Subtitles founded.', stream.id)

            # Run postprocessing
            params = download_config._gen_ydl_params(music_meta=stream._is_music_site())

            downloaded_file = run_postproces(
                file=downloaded_file,
                info=stream._extra_info,
                params=params,
            )
            log.debug(
                '"%s": Postprocessing finished, saved as "%s".',
                stream.id,
                downloaded_file.suffix[1:],
            )

            # STATUS: Finish
            final_path = Path(self.config.output, output_name + downloaded_file.suffix)

            # Check if file is duplicate
            if final_path.exists():
                self._progress.update(task_id, status="Skipped")
                log.info(
                    'Skipped: "%s" (Exists as "%s").',
                    stream.display_name,
                    final_path.suffix[1:],
                )
            # Move file
            else:
                self.config.output.mkdir(parents=True, exist_ok=True)

                downloaded_file = downloaded_file.rename(
                    downloaded_file.parent / final_path.name
                )
                final_path = shutil.move(downloaded_file, final_path)

                self._progress.update(task_id, status="Finished")
                log.info('Finished: "%s".', stream.display_name)

            if on_progress:
                on_progress("finished", total_filesize, total_filesize)

            return final_path
        except MediaError as err:
            log.error('Error: "%s": %s', stream.display_name, str(err))
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
            case LazyStreams():
                streams = media._list
            case Playlist():
                streams = media.streams._list
            case _:
                raise TypeError(media)

        return streams

    def _resolve_format(
        self,
        stream: Stream,
        format: Format | None = None,
    ) -> tuple[Format, FormatConfig]:
        config = self.config

        if format:
            if format not in stream.formats:
                raise ValueError(f"'{format.id}' format ID not founded in Stream.")

            if not config.convert:
                config.format = format.type
        else:
            if not config.convert and stream._is_music_site():
                log.debug(
                    '"%s": Detected music site, change config to "audio".',
                    stream.id,
                )
                config.format = "audio"

            format = self._extract_best_format(stream.formats, config)

            if not config.convert and config.type != format.type:
                log.debug(
                    '"%s": Format "%s" and config "%s" missmatch, change config to "%s".',
                    stream.id,
                    format.type,
                    config.type,
                    format.type,
                )
                config.format = format.type

        return format, config

    def _extract_best_format(
        self, formats: FormatList, custom_config: FormatConfig | None = None
    ) -> Format:
        """Extract best format in stream formats."""

        config = custom_config if custom_config else self.config

        # Filter by extension
        if f := config.convert and formats.filter(extension=config.convert):
            format = f
        # Filter by type
        elif f := formats.filter(type=config.type):
            format = f
        # Filter fallback to available type.
        elif f := formats.filter(type="video") or formats.filter(type="audio"):
            format = f
        else:
            raise TypeError("Not format matches founded.")

        if config.quality:
            return f.get_closest_quality(config.quality)
        else:
            return format[-1]
