from typing_extensions import Self
from pydantic import BaseModel

from media_dl.ydl.types import YDLExtractInfo


class Serializable(BaseModel):
    def to_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True)

    def to_ydl_json(self) -> str:
        return self.model_dump_json(by_alias=True)

    @classmethod
    def from_ydl_json(cls, data: str) -> Self:
        return cls.model_validate_json(data, by_alias=True)
