"""Media-DL API. Handler for URLs extraction, serialization and streams download."""

from typing import TYPE_CHECKING
import sys

from lazy_imports import LazyImporter

from media_dl.exceptions import DownloadError, ExtractError, MediaError

if TYPE_CHECKING:
    from media_dl.downloader.stream import StreamDownloader
    from media_dl.models.format import VideoFormat, AudioFormat
    from media_dl.models.playlist import Playlist
    from media_dl.models.stream import Stream

sys.modules[__name__] = LazyImporter(
    __name__,
    __file__,
    {
        "downloader.stream": ["StreamDownloader"],
        "models.format": ["VideoFormat", "AudioFormat"],
        "models.playlist": ["Playlist"],
        "models.stream": ["Stream"],
    },
)

__all__ = [
    "DownloadError",
    "ExtractError",
    "MediaError",
    "StreamDownloader",
    "VideoFormat",
    "AudioFormat",
    "Stream",
    "Playlist",
]
