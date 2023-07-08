from typing import List
from pathlib import Path
import sys

from spotipy import Spotify, SpotifyException, CacheFileHandler
from spotipy.oauth2 import SpotifyClientCredentials

from spotdl import Downloader
from spotdl.types.song import Song
from spotdl.utils.search import parse_query
from spotdl.utils.logging import init_logging
from spotdl.utils.config import create_settings, get_config, get_cache_path, DEFAULT_CONFIG, SPOTIFY_OPTIONS
from spotdl.utils.arguments import parse_arguments
from spotdl.utils.spotify import SpotifyClient, save_spotify_cache
from spotdl.console.entry_point import generate_initial_config, OPERATIONS

VALID_URLS = ("https://open.spotify.com/playlist/")

def check_spotify_url(url: str) -> str:
	sp = get_SpotifyClient()

	if sp.playlist(url):
		return url
	else:
		raise ValueError

def get_SpotifyClient():
	config = DEFAULT_CONFIG

	auth_manager = SpotifyClientCredentials(
		client_id=config["client_id"],
		client_secret=config["client_secret"],
		cache_handler=CacheFileHandler(cache_path=get_cache_path())
	)
	return Spotify(auth_manager=auth_manager)

class Spotdl():
	# Singleton
	def __new__(cls, *args, **kwargs):
		if not hasattr(cls, "instance"):
			SpotifyClient.init(**SPOTIFY_OPTIONS)
			init_logging("INFO")
			cls.instance = super(Spotdl, cls).__new__(cls)
		return cls.instance

	def __init__(self, audio_format: str, output_path: Path):
		config: dict = DEFAULT_CONFIG

		config["format"] = audio_format
		config["output"] = str(f"{output_path}" + "/" + "{artists} - {title}.{output-ext}")
		config["lyrics_providers"] = ["synced", "musixmatch", "genius"]
		config["bitrate"] = "disable"

		self.downloader_settings = config

	def search(self, query: List[str]):
		return parse_query(query, threads=4)

	def download_songs(self, songs: List[Song]):
		downloader = Downloader(self.downloader_settings)
		downloader.download_multiple_songs(songs)
		downloader.progress_handler.close()