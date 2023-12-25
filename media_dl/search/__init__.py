from enum import Enum

from media_dl.search import piped, soundcloud, ytmusic


class SearchProvider(Enum):
    soundcloud = soundcloud.SoundCloud
    ytmusic = ytmusic.YTMusic
    piped = piped.YouTubePiped
