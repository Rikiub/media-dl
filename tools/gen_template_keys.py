#!/usr/bin/env python

import json
from pathlib import Path

from pydantic import BaseModel

from media_dl.models.format import AudioFormat, Format, VideoFormat, YDLArgs
from media_dl.models.playlist import Playlist
from media_dl.models.stream import Stream

FILEPATH = Path("template.json")


def _keys(model: type[BaseModel], by_alias: bool = False) -> list[str]:
    keys = []

    for name, info in model.model_fields.items():
        if by_alias and info.alias:
            keys.append(info.alias)
        else:
            keys.append(name)

    return keys


EXCLUDED_KEYS = [
    *_keys(YDLArgs),
    "streams",
    "formats",
    "subtitles",
    "thumbnails",
    "datetime",
    "extension",
    "ext",
]

OUTPUT_TEMPLATES = [
    *_keys(Playlist, True),
    *_keys(Stream),
    *_keys(Format),
    *_keys(VideoFormat),
    *_keys(AudioFormat, True),
]

for key in EXCLUDED_KEYS:
    OUTPUT_TEMPLATES.remove(key)

with FILEPATH.open("w") as f:
    json.dump(OUTPUT_TEMPLATES, f)
