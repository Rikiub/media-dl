from media_dl.models.format import Format
from media_dl.models.stream import Stream
from media_dl.models.playlist import Playlist

ExtractResult = list[Stream] | Playlist | Stream
