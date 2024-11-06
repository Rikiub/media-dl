"""Media-DL API. Handler for URLs extraction, serialization and streams download."""

from typing import TYPE_CHECKING
import sys

from lazy_imports import LazyImporter

from media_dl.exceptions import DownloadError, ExtractError, MediaError

if TYPE_CHECKING:
    from media_dl.downloader.stream import StreamDownloader
    from media_dl.extractor.stream import extract_search, extract_url
    from media_dl.models.format import Format, VideoFormat, AudioFormat
    from media_dl.models.playlist import Playlist
    from media_dl.models.stream import Stream

sys.modules[__name__] = LazyImporter(
    __name__,
    __file__,
    {
        "downloader.stream": ["StreamDownloader"],
        "extractor.stream": ["extract_url", "extract_search"],
        "models.format": ["Format", "VideoFormat", "AudioFormat"],
        "models.playlist": ["Playlist"],
        "models.stream": ["Stream"],
    },
)

__all__ = [
    "DownloadError",
    "ExtractError",
    "MediaError",
    "StreamDownloader",
    "extract_search",
    "extract_url",
    "Format",
    "VideoFormat",
    "AudioFormat",
    "Stream",
    "Playlist",
]
