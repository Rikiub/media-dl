from pathlib import Path

from pydantic import BaseModel
from pathvalidate import sanitize_filepath

from media_dl.exceptions import OutputTemplateError
from media_dl.models.format import AudioFormat, Format, VideoFormat, YDLArgs
from media_dl.models.playlist import Playlist
from media_dl.models.stream import Stream
from media_dl.types import StrPath


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


def _keys(model: type[BaseModel], by_alias: bool = False) -> list[str]:
    keys = []

    for name, info in model.model_fields.items():
        if by_alias and info.alias:
            keys.append(info.alias)
        else:
            keys.append(name)

    return keys


EXCLUDED_KEYS = frozenset(
    {
        *_keys(YDLArgs),
        "streams",
        "formats",
        "subtitles",
        "thumbnails",
        "datetime",
        "extension",
        "ext",
    }
)
OUTPUT_TEMPLATES = {
    *_keys(Playlist, True),
    *_keys(Stream),
    *_keys(Format),
    *_keys(VideoFormat),
    *_keys(AudioFormat, True),
}

for key in EXCLUDED_KEYS:
    OUTPUT_TEMPLATES.discard(key)

OUTPUT_TEMPLATES = frozenset(OUTPUT_TEMPLATES)
