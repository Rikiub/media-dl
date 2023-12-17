from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from spotipy import SpotifyClientCredentials, CacheFileHandler
from platformdirs import PlatformDirs

APPNAME = "media-dl"

dirs = PlatformDirs(APPNAME, ensure_exists=True)
DIR_DOWNLOAD = dirs.user_downloads_path / APPNAME
DIR_TEMP = dirs.site_cache_path

SPOTIPY_CACHE = DIR_TEMP / "spotipy.cache"
SPOTIPY_CREDENTIALS = SpotifyClientCredentials(
    client_id="c0e5d118c80b418db97f377e6399bb9d",
    client_secret="6b64af3eac544a96a5cd7d57a6a9323f",
    cache_handler=CacheFileHandler(cache_path=SPOTIPY_CACHE),
)


@dataclass(slots=True)
class Main:
    output_dir: Path
    threads: int
    parse_metadata: bool


@dataclass(slots=True)
class Extensions:
    video: str
    video_quality: str
    audio: str
    audio_quality: int
