from typing import TypeVar, cast
from media_dl.downloader.config import FormatConfig
from media_dl.models.formats.list import FormatList
from media_dl.models.formats.types import AudioFormat, Format, VideoFormat
from media_dl.models.stream import Stream

T = TypeVar("T", bound=Format)


class FormatSelector:
    """Responsible for selecting the best video/audio formats based on config."""

    def __init__(self, config: FormatConfig):
        self.config = config

    def resolve(self, stream: Stream) -> tuple[VideoFormat | None, AudioFormat | None]:
        """Resolves the final pair of formats to be downloaded."""
        video = self.extract_best(stream.formats, VideoFormat)
        audio = self.extract_best(stream.formats, AudioFormat)

        if not self.config.convert:
            if audio and (stream.is_music or self.config.format == "audio"):
                self.config.format = "audio"
                return None, audio
            elif video:
                self.config.format = "video"

        return video, audio

    def extract_best(self, formats: FormatList, type: type[T]) -> T | None:
        # Get type
        candidates = (
            formats.only_video()
            if issubclass(type, VideoFormat)
            else formats.only_audio()
        )

        if not candidates:
            return None

        # Filter by extension
        if self.config.convert:
            if filtered := candidates.filter(extension=self.config.convert):
                candidates = filtered

        if self.config.quality:
            # Resolve Quality
            result = candidates.get_closest_quality(self.config.quality)
        else:
            result = candidates[0]

        return cast(T, result)
