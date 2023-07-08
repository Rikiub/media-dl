from typing import List, Literal
from logging import Logger
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor import PostProcessor

FORMAT_EXTS: dict = YoutubeDL._format_selection_exts
THUMBNAIL_EXTS = {"mp3", "mkv", "mka", "ogg", "opus", "flac", "m4a", "mp4", "mov"}
VIDEO_QUALITY = ("144", "240", "360", "480", "720", "1080", "1440", "2160", "4320")
SEARCH: tuple = Literal["ytsearch"]

class ExtTypeError(Exception):
	"""Handler to EXT type errors"""

class QualityTypeError(Exception):
	"""Handler to quality"""

class YDL():
	def __init__(self,
		output_path: Path,
		cache_path=".temp",
		progress_hook=None,
		logger: Logger = None
	):
		self.progress_hook = progress_hook
		self.logger = logger
		self.ydl_opts = {
			"ignoreerrors": False,
			"simulate": False,
			"quiet": False,
			"paths": {
				"home": str(output_path),
				#"temp": str(cache_path)
			},
			"outtmpl": "%(title)s.%(ext)s",
			"format": str,
			"format_sort": [],
			"writethumbnail": True,
			"writesubtitles": True,
			"subtitleslangs": "all",
			"postprocessors": [
				{
					"key": "FFmpegMetadata",
					"add_metadata": True,
					"add_chapters": True,
				}
			]
		}
		if self.progress_hook:
			self.ydl_opts.update({"progress_hooks": [self.progress_hook]})
		if self.logger:
			self.ydl_opts.update({"logger": self.logger})

	"""
	# progress_hook example
	@staticmethod
	def progress_hook(task) -> None:
		if task["status"] == "downloading":
			task[""]
		if task["status"] == "finished":
	   		print('\nDone downloading, now post-processing ...\n')
	"""

	@staticmethod
	def extract_info(url: str) -> str:
		try:
			with YoutubeDL() as ydl:
				return ydl.extract_info(url, download=False)
		except:
			raise

	def create_ydl_opts(self, ext: Literal[FORMAT_EXTS], ext_quality=None) -> dict:
		ydl_opts = self.ydl_opts

		if ext in THUMBNAIL_EXTS:
			ydl_opts["postprocessors"].append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

		if ext in FORMAT_EXTS["video"]:
			try:
				if ext_quality is None:
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

		elif ext in FORMAT_EXTS["audio"]:
			ydl_opts["format"] = f"{ext}/bestaudio/best"
			ydl_opts["format_sort"] = [f"ext:{ext}:m4a:ogg:mp3"]
			ydl_opts["postprocessors"].append({"key": "FFmpegExtractAudio", "preferredcodec": ext, "preferredquality": ext_quality})

		else:
			raise ExtTypeError('Failed to determine the "ext" type. Expected:', FORMAT_EXTS["video"], FORMAT_EXTS["audio"])

		return ydl_opts

	def search(self, query: str, search: SEARCH):
		with YoutubeDL() as ydl:
			return ydl.extract_info(f"{search}:{query}", download=False)['entries'][0:5]

	def download(self,
		url: List[str],
		ext: Literal[FORMAT_EXTS],
		quality=None
	) -> bool:
		ydl_opts = self.create_ydl_opts(ext, ext_quality=quality)

		with YoutubeDL(ydl_opts) as ydl:
			error_code = ydl.download(url)
			return error_code

if __name__ == "__main__":
	path = Path(__file__).parent.parent.parent / "tests" / "yt-dlp"
	path.mkdir(parents=True, exist_ok=True)

	ydl = YDL(path)
	ydl.download("https://www.youtube.com/watch?v=BaW_jenozKc", "mp3")

"""
class MetadataPP(PostProcessor):
	def run(self, object_data):
		spotdl = get_spotdl_istance()

		query = str(object_data["uploader"] + " - " + object_data["fulltitle"])

		spotdl_meta = spotdl.search([query])
		print(spotdl_meta)

		return [], object_data  # return modified information
"""