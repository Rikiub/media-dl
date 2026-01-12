from typing import Literal

from media_dl.models.progress.base import HasFile

ProcessorType = Literal[
    "starting",
    "change_container",
    "convert_audio",
    "merge_formats",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]
ProcessorStage = Literal["started", "completed"]


class ProcessingState(HasFile):
    status: Literal["processing"] = "processing"
    stage: ProcessorStage
    processor: ProcessorType = "starting"
