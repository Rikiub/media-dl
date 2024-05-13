from pathlib import Path
from typing import Callable, cast

from yt_dlp import DownloadError as YTDLP_DownloadError

from media_dl._ydl import YTDLP, InfoDict, format_except_message
from media_dl.exceptions import DownloadError
from media_dl.models.format import Format

DownloadCallback = Callable[[int, int], None]


def download(
    filepath: Path,
    format: Format,
    callbacks: list[DownloadCallback] | None = None,
) -> Path:
    """Download format.

    Returns:
        Filepath to file.

    Raises:
        DownloadError: Download failed.
    """

    params = {}

    if callbacks:
        wrappers = [lambda d: _progress_wraper(d, callback) for callback in callbacks]
        params |= {"progress_hooks": wrappers}

    params |= {"outtmpl": f"{filepath}.%(ext)s"}
    format_dict = _gen_generic_info(format)

    info = _internal_download(format_dict, params)

    path = info["requested_downloads"][0]["filepath"]
    return Path(path)


def _internal_download(info: InfoDict, params: dict) -> InfoDict:
    retries = {"retries": 0, "fragment_retries": 0}

    try:
        info = YTDLP(retries | params).process_ie_result(info, download=True)
        return cast(InfoDict, info)
    except YTDLP_DownloadError as err:
        msg = format_except_message(err)
        raise DownloadError(msg)


def _gen_generic_info(format: Format) -> InfoDict:
    return InfoDict(
        {
            "extractor": "generic",
            "extractor_key": "Generic",
            "title": format.id,
            "id": format.id,
            "formats": [format._format_dict()],
            "format_id": format.id,
        }
    )


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
