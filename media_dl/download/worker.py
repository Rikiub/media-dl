from pathlib import Path
from typing import Callable, cast

from yt_dlp import DownloadError as BaseDownloadError

from media_dl._ydl import YTDLP, InfoDict, format_except_message
from media_dl.exceptions import DownloadError
from media_dl.models.format import Format

DownloadCallback = Callable[[int, int], None]


def download(
    filepath: Path,
    video: Format | None,
    audio: Format | None,
    merge_format: str | None = None,
    callbacks: list[DownloadCallback] | None = None,
) -> Path:
    """Download format.

    Returns:
        Filepath to file.

    Raises:
        DownloadError: Download failed.
    """

    if not (video or audio):
        raise ValueError("No formats to download.")

    # Params
    params = {}

    if merge_format:
        params |= {"merge_output_format": merge_format}

    if callbacks:
        wrappers = [lambda d: _progress_wraper(d, callback) for callback in callbacks]
        params |= {"progress_hooks": wrappers}

    params |= {"outtmpl": f"{filepath}.%(ext)s"}

    # InfoDict
    format_id = f"{video.id if video else ""}+{audio.id if audio else ""}"

    if format_id.startswith("+") or format_id.endswith("+"):
        format_id = format_id.strip("+")

    formats: list[InfoDict] = []

    if video:
        formats.append(video.as_dict())
    if audio:
        formats.append(audio.as_dict())

    info = {
        "extractor": "generic",
        "extractor_key": "Generic",
        "title": filepath.stem,
        "id": filepath.stem,
        "formats": formats,
        "requested_formats": formats,
        "format_id": format_id,
    }

    info = _internal_download(info, params)

    path = info["requested_downloads"][0]["filepath"]
    return Path(path)


def _internal_download(info: dict, params: dict) -> InfoDict:
    retries = {"retries": 0, "fragment_retries": 0}

    try:
        info = YTDLP(retries | params).process_ie_result(info, download=True)
        return cast(InfoDict, info)
    except BaseDownloadError as err:
        msg = format_except_message(err)
        raise DownloadError(msg)


def _progress_wraper(d: dict, callback: DownloadCallback) -> None:
    """`YT-DLP` progress hook, but stable and without issues."""

    status: str = d.get("status") or ""
    completed: int = d.get("downloaded_bytes") or 0
    total: int = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

    match status:
        case "downloading":
            callback(completed, total)
        case "finished":
            callback(total, total)
