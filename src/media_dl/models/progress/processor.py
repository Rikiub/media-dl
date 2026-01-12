from typing import Literal

from media_dl.models.progress.base import HasFile
from media_dl.processor import ProcessorType

ProcessorStateType = Literal["starting", ProcessorType]
ProcessorStateStage = Literal["started", "completed"]


class ProcessingState(HasFile):
    status: Literal["processing"] = "processing"
    stage: ProcessorStateStage
    processor: ProcessorStateType = "starting"
