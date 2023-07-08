from pathlib import Path
import shlex

from theme import print, input
from downloader import Downloader

def TUI() -> None:
	CWD = Path.cwd()
	OUTPUT_PATH = Path("tests", "downloads")
	CACHE_PATH = Path("tests", ".temp")

	# TEST URL
	url_list = ["https://www.youtube.com/watch?v=BaW_jenozKc"]

	query = input("Write songs name: ")
	query = shlex.split(query)

	dl = Downloader(OUTPUT_PATH, CACHE_PATH)

	#dl.audio(url_list, "m4a")
	#dl.video(url_list, "mp4", quality="480")
	while True:
		dl.music(query, "m4a")
		dl.music(query, "mp3")

if __name__ == "__main__":
	TUI()