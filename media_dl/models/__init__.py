"""Models to represent extraction results."""

from media_dl.models.format import Format
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStreams, Stream

__all__ = ["Format", "Playlist", "Stream", "LazyStreams"]

ExtractResult = Playlist | LazyStreams | Stream
