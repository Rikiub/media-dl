from pathlib import Path

from pydantic import BaseModel


class State(BaseModel):
    id: str


class HasFile(State):
    filepath: Path

    @property
    def extension(self) -> str:
        return self.filepath.suffix[1:]
