from pathlib import Path
from typing import Annotated, Callable, Literal, cast, get_args

from pydantic import BaseModel, Field
from yt_dlp import DownloadError as BaseDownloadError

from media_dl._ydl import YTDLP, format_except_message
from media_dl.exceptions import DownloadError, PostProcessingError
from media_dl.models.format import Format
from media_dl.types import FORMAT_TYPE, VIDEO_EXTENSION, InfoDict


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


class YDLDownloader:
    def __init__(
        self,
        filepath: Path,
        video: Format | None,
        audio: Format | None,
        merge_format: str | None = None,
        callbacks: list[DownloadCallback] | None = None,
    ) -> None:
        if not (video or audio):
            raise ValueError("No formats to download.")

        # Variables
        self.params: dict = {}
        self.info: dict = {}
        self.progress: ProgressStatus = ProgressStatus()

        # Params
        if merge_format:
            self.params |= {
                "merge_output_format": merge_format
                or "/".join(get_args(VIDEO_EXTENSION))
            }

        if callbacks:
            wrappers = [lambda d: self._progress_wraper(d, c) for c in callbacks]
            self.params |= {"progress_hooks": wrappers}
            self.progress = ProgressStatus(
                status="waiting",
                step_type="video" if video else "audio",
                steps_total=2 if video and audio else 1,
            )

        self.params |= {"outtmpl": {"default": f"{filepath}.%(ext)s"}}

        # Info
        format_id = (
            str(video.id if video else "") + "+" + str(audio.id if audio else "")
        )

        if format_id.startswith("+") or format_id.endswith("+"):
            format_id = format_id.strip("+")

        formats: list[InfoDict] = [
            f.model_dump(by_alias=True) for f in (video, audio) if f is not None
        ]

        self.info = {
            "extractor": "generic",
            "extractor_key": "Generic",
            "title": filepath.stem,
            "id": filepath.stem,
            "formats": formats,
            "format_id": format_id,
        }

    def run(self) -> Path:
        info = self._internal_download(self.info, self.params)
        path = info["requested_downloads"][0]["filepath"]
        return Path(path)

    def _internal_download(self, info: dict, params: dict) -> InfoDict:
        retries = {"retries": 0, "fragment_retries": 0}

        try:
            info = YTDLP(retries | params).process_ie_result(info, download=True)
            return cast(InfoDict, info)
        except BaseDownloadError as err:
            msg = format_except_message(err)

            if "Postprocessing:" in msg:
                raise PostProcessingError(msg)
            else:
                raise DownloadError(msg)

    def _progress_wraper(self, d: dict, callback: DownloadCallback) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        if self.progress:
            p = self.progress

            match d["status"]:
                case "downloading":
                    p.status = "downloading"

                    p.downloaded_bytes = d.get("downloaded_bytes") or 0
                    total_bytes = (
                        d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    )

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
