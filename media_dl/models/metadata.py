from pydantic import BaseModel


class Thumbnail(BaseModel):
    id: str
    url: str
    width: int
    height: int
