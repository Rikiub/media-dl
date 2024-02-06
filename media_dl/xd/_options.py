from typing import Annotated
from pathlib import Path
from enum import Enum

from typer import Argument, Option


OutputOptional = Annotated[
    Path,
    Option(
        "--output",
        "-o",
        help="Directory where to save downloads.",
        file_okay=False,
        resolve_path=True,
        show_default=False,
    ),
]


class Format(Enum):
    video = "video"
    audio = "audio"


FormatOption = Annotated[
    Format,
    Option(
        "--format",
        "-f",
        help="File type to request. Would fallback to 'audio' if 'video' is not available.",
        show_default=False,
        prompt="What format you want?",
    ),
]
