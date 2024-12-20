from pathlib import Path
from media_dl.models.format import AudioFormat, Format, VideoFormat
from media_dl.models.stream import Stream
from media_dl.types import StrPath


def generate_output_template(
    output: StrPath, stream: Stream, format: Format | None = None
) -> Path:
    data = {}

    data |= stream.model_dump()
    data |= stream.model_dump(by_alias=True)
    if format:
        data |= format.model_dump()
        data |= format.model_dump(by_alias=True)

    result = str(output).format(**data)
    result = result[:265]  # String length limit
    return Path(result)


OUTPUT_TEMPLATES = frozenset(
    {
        *Stream.model_fields.keys(),
        *VideoFormat.model_fields.keys(),
        *AudioFormat.model_fields.keys(),
    }
)
