"""Models to represent extraction results."""

from media_dl.models.format import Format
from media_dl.models.stream import Stream, LazyStreams
from media_dl.models.playlist import Playlist

ExtractResult = Playlist | LazyStreams | Stream
