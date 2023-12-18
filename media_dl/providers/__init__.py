from typing import Literal
from enum import Enum

from media_dl.providers.base import SearchProvider
from media_dl.providers import piped, soundcloud, ytmusic


class Providers(Enum):
    soundcloud = soundcloud.Soundcloud
    ytmusic = ytmusic.YTMusic
    piped = piped.YouTubePiped


PROVIDER = Literal["soundcloud", "ytmusic", "piped"]


def get_provider(provider: PROVIDER) -> SearchProvider:
    try:
        return Providers[provider].value()
    except:
        raise ValueError(f"{provider} is a invalid option, must be:", PROVIDER)
