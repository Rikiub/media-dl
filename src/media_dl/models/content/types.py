from pydantic import TypeAdapter

from media_dl.models.content.media import LazyMedia, Media
from media_dl.models.content.list import LazyPlaylist, Playlist

ExtractResult = Media | Playlist
ExtractAdapter = TypeAdapter[ExtractResult](ExtractResult)

MediaListEntries = LazyMedia | LazyPlaylist
MediaListAdapter = TypeAdapter[MediaListEntries](MediaListEntries)
