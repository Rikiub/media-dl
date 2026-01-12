from typing import TypeVar, cast

from media_dl.downloader.config import FormatConfig
from media_dl.models.content.media import Media
from media_dl.models.format.list import FormatList
from media_dl.models.format.types import AudioFormat, Format, VideoFormat

T = TypeVar("T", bound=Format)


class FormatSelector:
    """Responsible for selecting the best video/audio formats based on config."""

    def __init__(self, config: FormatConfig):
        self._config = config

    def resolve(self, media: Media) -> tuple[VideoFormat | None, AudioFormat | None]:
        """Resolves the final pair of formats to be downloaded."""
        audio = self.extract_best(media.formats, AudioFormat)

        if audio and (media.is_music or self._config.type == "audio"):
            return None, audio

        video = self.extract_best(media.formats, VideoFormat)
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
        if self._config.convert:
            if filtered := candidates.filter(extension=self._config.convert):
                candidates = filtered

        if self._config.quality:
            # Resolve Quality
            result = candidates.get_closest_quality(self._config.quality)
        else:
            result = candidates[0]

        return cast(T, result)
