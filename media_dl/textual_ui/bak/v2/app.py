from typing import Literal

from platformdirs import user_downloads_dir

from textual.app import App, ComposeResult
from textual import work
from textual.reactive import reactive
from textual.containers import (
	Center
)
from textual.widgets import (
	Static,
	Label,
	Input,
	Button,
	Select,
	Log
)

from _yt_dlp import YDL, FORMAT_EXTS, VIDEO_QUALITY

MODE = {
	"video": "video",
	"audio": "audio"
}
MODE_TEXT = {
	"video": "📹Video",
	"audio": "🔊Audio"
}
class Operation(Center):
	"""Main Widget to get the QueryBox settings"""
	mode = reactive(MODE["video"])

	def watch_mode(self, mode):
		self.query_one("#operation-audio-ext").set_class(not(mode in MODE["audio"]), "hidden")
		self.query_one("#operation-video-ext").set_class(not(mode in MODE["video"]), "hidden")
		self.query_one("#operation-video-quality").set_class(not(mode in MODE["video"]), "hidden")

	async def on_button_pressed(self, event: Button.Pressed) -> None:
		"""The changer to the 'mode' variable"""
		button_id = event.button.id
		if button_id in MODE:
			self.mode = button_id
		else:
			raise ValueError

	def compose(self) -> None:
		# Top Operations
		with Static(id="operations"):
			yield Button(MODE_TEXT["video"], id="video")
			yield Button(MODE_TEXT["audio"], id="audio")

		with Center():
			# Selectors
			with Static(id="operation"):
				yield Select(
					list(zip(FORMAT_EXTS["audio"], FORMAT_EXTS["audio"])),
					prompt="EXT Audio", id="operation-audio-ext")
				yield Select(
					list(zip(FORMAT_EXTS["video"], FORMAT_EXTS["video"])),
					prompt="EXT Video", id="operation-video-ext")
				yield Select(
					[(item + "p", item) for item in VIDEO_QUALITY],
					prompt="Quality", id="operation-video-quality")

			# InputBox
			with Static(id="inputbox"):
				yield Label("Insert a URL", id="inputbox-log")
				yield Input("", placeholder="Search something...", id="inputbox-input")
				#yield Button("✅", id="inputbox-confirm")

class YDLApp(App):
	TITLE = "YDL"
	CSS_PATH = "styles.tcss"
	BINDINGS = [
		("d", "toggle_dark", "Toggle dark mode")
	]

	def compose(self) -> ComposeResult:
		yield Operation()
		yield Log(id="logger")

	def on_input_submitted(self, event: Input.Submitted) -> None:
		if event.input.id == "inputbox-input":
			self.start_download(event.input.value)

	@work(exclusive=True, thread=True)
	def start_download(self, url: str) -> None:
		ydl = YDL()
		mode = self.query_one(Operation).mode

		if mode == "video":
			ext = self.query_one("#operation-video-ext").value
			ext_quality = self.query_one("#operation-video-quality").value
			ydl.download(
				url=url,
				ext=ext,
				output_path=user_downloads_dir(),
				quality=ext_quality
			)
			self.query_one("#logger").write_line("Video download completed!")
		elif mode == "audio":
			ext = self.query_one("#operation-audio-ext").value
			ydl.download(
				url=url,
				ext=ext,
				output_path=user_downloads_dir()
			)
			self.query_one("#logger").write_line("Audio download completed!")

if __name__ == "__main__":
	app = YDLApp()
	app.run()