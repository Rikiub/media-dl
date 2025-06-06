import re
from pathlib import Path
from typing import Literal

from pathvalidate import sanitize_filepath

from media_dl.exceptions import OutputTemplateError
from media_dl.models.format import Format
from media_dl.models.playlist import Playlist
from media_dl.models.stream import Stream
from media_dl.template.keys import OUTPUT_TEMPLATES
from media_dl.types import StrPath


def generate_output_template(
    output: StrPath,
    stream: Stream,
    playlist: Playlist | None = None,
    format: Format | None = None,
) -> Path:
    validate_output(output)

    data = {}

    if format:
        data |= format.model_dump()
        data |= format.model_dump(by_alias=True)
    if playlist:
        data |= playlist.model_dump(by_alias=True)
    if stream:
        data |= stream.model_dump()

    template = str(output).format(**data)
    path = Path(sanitize_filepath(template, max_len=250))
    return path


def validate_output(output: StrPath) -> Literal[True]:
    pattern = r"{(.*?)}"
    keys: list[str] = re.findall(pattern, str(output))

    for key in keys:
        if key not in OUTPUT_TEMPLATES:
            raise OutputTemplateError(f"Key '{{{key}}}' from '{output}' is invalid.")

    return True
