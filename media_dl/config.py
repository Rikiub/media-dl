from spotipy import SpotifyClientCredentials, CacheFileHandler
from platformdirs import PlatformDirs

APPNAME = "media-dl"

dirs = PlatformDirs(APPNAME, ensure_exists=True)
DIR_DOWNLOAD = dirs.user_downloads_path / APPNAME
DIR_CACHE = dirs.user_cache_path

SPOTIPY_CACHE = DIR_CACHE / "spotipy.cache"
SPOTIPY_CREDENTIALS = SpotifyClientCredentials(
    client_id="c0e5d118c80b418db97f377e6399bb9d",
    client_secret="6b64af3eac544a96a5cd7d57a6a9323f",
    cache_handler=CacheFileHandler(cache_path=SPOTIPY_CACHE),
)
