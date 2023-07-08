from typing import List, Literal
from pathlib import Path

from providers._yt_dlp import YDL, FORMAT_EXTS, VIDEO_QUALITY, ExtTypeError
from providers._spotdl import Spotdl, check_spotify_url

class Downloader():
	def __init__(self, output_path: Path, cache_path: Path):
		self.output_path = output_path
		self.cache_path = cache_path

	def video(self,
		url: List[str],
		video_format: Literal[FORMAT_EXTS],
		quality: Literal[VIDEO_QUALITY] = None
	) -> None:

		if video_format in FORMAT_EXTS["video"]:
			ydl = YDL(
				output_path=self.output_path / "Video",
				cache_path=self.cache_path
			)
			ydl.download(url, video_format, quality=quality)
		else:
			raise ExtTypeError

	def audio(self,
		url: List[str],
		audio_format: Literal[FORMAT_EXTS]
	) -> None:

		if audio_format in FORMAT_EXTS["audio"]:
			ydl = YDL(
				output_path=self.output_path / "Audio",
				cache_path=self.cache_path
			)
			ydl.download(url, audio_format)
		else:
			raise ExtTypeError

	def music(
		self,
		query: List[str],
		audio_format: Literal[FORMAT_EXTS]
	) -> None:

		spotdl = Spotdl(
			audio_format,
			output_path=self.output_path / "Music",
			#cache_path=self.cache_path
		)

		spotdl.download_songs(
			spotdl.search(query)
		)