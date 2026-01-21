from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class State(BaseModel):
    id: str


class HasFile(State):
    filepath: Path

    @property
    def extension(self) -> str:
        return self.filepath.suffix[1:]


StageType = Literal["started", "completed"]
