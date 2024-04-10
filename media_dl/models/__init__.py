from media_dl.models.stream import Stream
from media_dl.models.playlist import Playlist
from media_dl.models.format import Format

ExtractResult = list[Stream] | Playlist | Stream
