from media_dl.models.stream import Stream, StreamList, Format
from media_dl.models.list import Playlist

Downloadable = Stream | Format
ExtractResult = Playlist | StreamList | Stream
