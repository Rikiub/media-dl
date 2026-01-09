from pathlib import Path
from typing import Annotated, Callable, Literal, get_args

from pydantic import BaseModel, Field

from media_dl.models.formats.types import Format
from media_dl.types import FORMAT_TYPE, VIDEO_EXTENSION
from media_dl.ydl.helpers import download_from_info
from media_dl.ydl.types import YDLExtractInfo, YDLParams


class ProgressStatus(BaseModel):
    status: Literal[
        "waiting", "downloading", "merging", "postprocessing", "finished"
    ] = "waiting"

    step_type: FORMAT_TYPE = "video"
    steps_completed: int = 0
    steps_total: int = 0

    fragments_completed: Annotated[int, Field(alias="fragment_index")] = 0
    """Available if `step_type` is video."""
    fragments_total: Annotated[int, Field(alias="fragment_count")] = 0
    """Available if `step_type` is video."""

    speed: float = 0
    elapsed: float = 0

    downloaded_bytes: float = 0
    total_bytes: float = 0


DownloadCallback = Callable[[ProgressStatus | None], None]


def download_formats(
    filepath: Path,
    video: Format | None,
    audio: Format | None,
    merge_format: str | None = None,
    callbacks: list[DownloadCallback] | None = None,
) -> tuple[Path, ProgressStatus]:
    if not (video or audio):
        raise ValueError("No formats to download.")

    # Variables
    params: YDLParams = {}
    info: YDLExtractInfo = {}
    progress: ProgressStatus = ProgressStatus()

    # Params
    if merge_format:
        params |= {
            "merge_output_format": merge_format or "/".join(get_args(VIDEO_EXTENSION))
        }

    if callbacks:
        params |= {
            "progress_hooks": [
                lambda d: _progress_wraper(d, call, progress) for call in callbacks
            ]
        }
        progress = ProgressStatus(
            status="waiting",
            step_type="video" if video else "audio",
            steps_total=2 if video and audio else 1,
        )

    params |= {"outtmpl": {"default": f"{filepath}.%(ext)s"}}

    # Info
    format_id = str(video.id if video else "") + "+" + str(audio.id if audio else "")

    if format_id.startswith("+") or format_id.endswith("+"):
        format_id = format_id.strip("+")

    formats: list[dict] = [f.to_ydl_dict() for f in (video, audio) if f is not None]

    info = {
        "extractor": "generic",
        "extractor_key": "Generic",
        "title": filepath.stem,
        "id": filepath.stem,
        "formats": formats,
        "format_id": format_id,
    }

    return download_from_info(info, params), progress


def _progress_wraper(
    data: dict,
    callback: DownloadCallback,
    progress: ProgressStatus,
) -> None:
    """`YT-DLP` progress hook, but stable and without issues."""

    d = data
    p = progress

    match d["status"]:
        case "downloading":
            p.status = "downloading"

            p.downloaded_bytes = d.get("downloaded_bytes") or 0
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

            if total_bytes > p.total_bytes:
                p.total_bytes = total_bytes

            p.fragments_completed = d.get("fragment_index") or 0
            p.fragments_total = d.get("fragment_count") or 0

            p.speed = d["speed"]
            p.elapsed = d["elapsed"]
        case "finished":
            if p.steps_completed < p.steps_total:
                p.downloaded_bytes = p.total_bytes
                p.steps_completed += 1

                if p.step_type == "video":
                    p.step_type = "audio"

            p.total_bytes = p.downloaded_bytes

    if p.steps_completed == p.steps_total:
        p.status = "merging"

    callback(p)
