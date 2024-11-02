from pydantic import BaseModel, OnErrorOmit


class Thumbnail(BaseModel):
    id: str
    url: str
    width: int = 0
    height: int = 0


ThumbnailList = list[OnErrorOmit[Thumbnail]]
