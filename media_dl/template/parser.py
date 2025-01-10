from pathlib import Path
import json

from pathvalidate import sanitize_filepath

from media_dl.exceptions import OutputTemplateError
from media_dl.models.format import Format
from media_dl.models.playlist import Playlist
from media_dl.models.stream import Stream
from media_dl.types import StrPath

FILEPATH = Path(Path(__file__).parent, "template.json")


def generate_output_template(
    output: StrPath,
    stream: Stream,
    playlist: Playlist | None = None,
    format: Format | None = None,
) -> Path:
    data = {}

    if format:
        data |= format.model_dump()
        data |= format.model_dump(by_alias=True)
    if playlist:
        data |= playlist.model_dump(by_alias=True)
    if stream:
        data |= stream.model_dump()

    try:
        template = str(output).format(**data)
    except KeyError as key:
        raise OutputTemplateError(f"Key {key} from '{output}' is invalid.")

    path = Path(sanitize_filepath(template, max_len=250))
    return path


def get_template_keys() -> list[str]:
    with FILEPATH.open() as f:
        return json.load(f)
