"""Read pre-serialized keys from JSON to improve startup time on shell autocomplete."""

import json
from pathlib import Path

_FILEPATH = Path(Path(__file__).parent, f"{Path(__file__).stem}.json")


def _gen_keys() -> list[str]:
    """Should be executed only one time if the file not exists."""

    from pydantic import BaseModel

    from media_dl.models.formats.types import AudioFormat, Format, VideoFormat, YDLArgs
    from media_dl.models.playlist import Playlist
    from media_dl.models.stream import Stream

    def extract(model: type[BaseModel], by_alias: bool = False) -> list[str]:
        keys: list[str] = []

        for name, info in model.model_fields.items():
            if by_alias and info.alias:
                keys.append(info.alias)
            else:
                keys.append(name)

        return keys

    EXCLUDED_KEYS = {
        *extract(YDLArgs),
        "streams",
        "formats",
        "subtitles",
        "thumbnails",
        "datetime",
        "extension",
        "ext",
    }

    templates = {
        *extract(Playlist, True),
        *extract(Stream),
        *extract(Format),
        *extract(VideoFormat),
        *extract(AudioFormat, True),
    }

    for key in EXCLUDED_KEYS:
        templates.discard(key)

    return list(templates)


if not _FILEPATH.is_file():
    keys = _gen_keys()
    _FILEPATH.write_text(json.dumps(keys))

with _FILEPATH.open() as f:
    OUTPUT_TEMPLATES: frozenset[str] = frozenset(json.load(f))
