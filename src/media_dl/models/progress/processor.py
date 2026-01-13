from typing import Annotated, Literal

from pydantic import Field

from media_dl.models.format.types import AudioFormat, VideoFormat
from media_dl.models.progress.base import HasFile

ProcessorStateType = Literal[
    "change_container",
    "convert_audio",
    "embed_metadata",
    "embed_thumbnail",
    "embed_subtitles",
]
ProcessorStateStage = Literal["started", "completed"]


class ProcessorState(HasFile):
    status: Literal["processing"] = "processing"
    stage: ProcessorStateStage
    processor: ProcessorStateType


class MergingProcessorState(ProcessorState):
    processor: Literal["merge_formats"] = "merge_formats"  # type: ignore

    video_format: VideoFormat
    audio_format: AudioFormat


ProcessingState = Annotated[
    MergingProcessorState | ProcessorState,
    Field(discriminator="processor"),
]
