from typing import Literal
from enum import Enum

from media_dl.providers import base, soundcloud, ytmusic


class Providers(Enum):
    soundcloud = soundcloud.Soundcloud
    ytmusic = ytmusic.YTMusic
    ydl = base.YDLGeneric


PROVIDER = Literal["soundcloud", "ytmusic", "ydl"]


def get_provider(provider: PROVIDER, format: tuple[str, int]) -> base.YDLGeneric:
    try:
        ins = Providers[provider].value
    except:
        ins = Providers.ydl.value

    return ins(extension=format[0], quality=format[1])
