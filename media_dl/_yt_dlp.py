"""better yt-dlp helper"""

from typing import List, Literal
from logging import Logger
from pathlib import Path

from yt_dlp import YoutubeDL

FORMAT_EXTS: dict = YoutubeDL._format_selection_exts
THUMBNAIL_EXTS = {"mp3", "mkv", "mka", "ogg", "opus", "flac", "m4a", "mp4", "mov"}
VIDEO_QUALITY = ("144", "240", "360", "480", "720", "1080", "1440", "2160", "4320")
SEARCH_PROVIDER = {"ytsearch"}

class ExtTypeError(Exception):
	"""Handler to EXT type errors"""

class QualityTypeError(Exception):
	"""Handler to quality"""

class YDL():
	"""_yt-dlp module main class"""

	def __init__(self,
		progress_hook=None,
		logger: Logger = None,
		quiet: bool = False
	):
		self.ydl_opts = {
			"quiet": quiet,
			"outtmpl": "%(title)s.%(ext)s",
			"format": str,
			"format_sort": [],
			"writethumbnail": True,
			"writesubtitles": True,
			"subtitleslangs": "all",
			"default_search": "auto",
			"postprocessors": []
		}
		if progress_hook:
			self.ydl_opts.update({"progress_hooks": [progress_hook]})
		if logger:
			self.ydl_opts.update({"logger": logger})

	def generate_ydl_opts(
		self,
		ext: Literal[FORMAT_EXTS],
		ext_quality=None
	) -> dict:
		"""YDL_OPTS Creator. Give it arguments and a custom config will be generated."""

		ydl_opts = self.ydl_opts
		ydl_opts["postprocessors"].append(
			{"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True}
		)

		# check if `ext` is Thumbnail compatible.
		if ext in THUMBNAIL_EXTS:
			ydl_opts["postprocessors"].append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

		# check if `ext` is video
		if ext in FORMAT_EXTS["video"]:
			try:
				if ext_quality is None:
					# if not quality, set to default (720p).
					ext_quality = VIDEO_QUALITY[5]
				else:
					index = VIDEO_QUALITY.index(ext_quality)
					ext_quality = VIDEO_QUALITY[index]
			except ValueError:
				raise QualityTypeError('Failed to determine the "quality" type. Expected:', *VIDEO_QUALITY)

			ydl_opts["format"] = f"bestvideo[height<={ext_quality}]+bestaudio/bestvideo[height<={ext_quality}]/best"
			ydl_opts["format_sort"] = [f"ext:{ext}:mp4:mkv"]
			ydl_opts["postprocessors"].append({"key": "FFmpegVideoConvertor", "preferedformat": ext})
			ydl_opts["postprocessors"].append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False})

		# check if `ext` is audio
		elif ext in FORMAT_EXTS["audio"]:
			ydl_opts["format"] = f"{ext}/bestaudio/best"
			ydl_opts["format_sort"] = [f"ext:{ext}:m4a:ogg:mp3"]
			ydl_opts["postprocessors"].append({"key": "FFmpegExtractAudio", "preferredcodec": ext, "preferredquality": ext_quality})

		else:
			raise ExtTypeError('Failed to determine the "ext" type. Expected:', FORMAT_EXTS["video"], FORMAT_EXTS["audio"])

		return ydl_opts

	def search(
		self,
		url: str
	) -> dict:
		with YoutubeDL(params=self.ydl_opts) as ydl:
			return ydl.extract_info(url, download=False)

	def search_multiple(
		self,
		query,
		search_provider: SEARCH_PROVIDER
	) -> dict:
		with YoutubeDL(params=self.ydl_opts) as ydl:
			if search_provider:
				return ydl.extract_info(f"{search_provider}:{query}", download=False)
			else:
				raise ValueError(
					f"You need to provide a 'search_provider' from the following options: {SEARCH_PROVIDER}"
				)

	def download(self,
		url: List[str],
		ext: Literal[FORMAT_EXTS],
		output_path: Path,
		quality=None
	) -> bool:
		"""Generate custom YDL_OPTS by `ext` and start download."""

		# get custom ydl_opts
		ydl_opts = self.generate_ydl_opts(ext, ext_quality=quality)
		ydl_opts.update({
			"paths": {"home": str(output_path)}
		})

		# start download
		with YoutubeDL(ydl_opts) as ydl:
			error_code = ydl.download(url)
			return error_code

if __name__ == "__main__":
	# Progress Hook example
	def progress_hook(task) -> None:
		if task["status"] == "downloading":
			print("\nDownloading...")
		if task["status"] == "finished":
	   		print('\nDownload completed')

	ydl = YDL(quiet=True, progress_hook=progress_hook)

	print("\n-> 'download' test")
	test_path = Path(__file__).parent.parent / "tests" / "yt-dlp"
	test_path.mkdir(parents=True, exist_ok=True)

	ydl.download("https://www.youtube.com/watch?v=BaW_jenozKc", "m4a", test_path)
	print("-> 'download' done")

	print("\n-> 'search' test")
	results = ydl.search("https://www.youtube.com/watch?v=BaW_jenozKc")
	print(results["title"])
	print("-> 'search' done")

	print("\n-> 'search_multiple' test")
	results = ydl.search_multiple("Lorem Ipsum", "ytsearch5")
	for entry in results["entries"]:
		print(entry["title"])
	print("-> 'search_multiple' done")