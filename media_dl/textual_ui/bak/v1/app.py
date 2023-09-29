from typing import Literal, List
from pathlib import Path

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual import work
from textual.worker import get_current_worker
from textual.containers import ScrollableContainer, HorizontalScroll, Horizontal, Container, Center
from textual.widgets import (
	Header,
	Footer,
	Button,
	Static,
	Input,
	TabbedContent,
	Select,
	Log,
	Label,
	Placeholder,
	LoadingIndicator
)

from _yt_dlp import FORMAT_EXTS, VIDEO_QUALITY, YDL

dl = YDL(
	output_path=Path(Path.home(), "media-dl")
)

MODE = {
	"video": "video",
	"audio": "audio"
}
MODE_TEXT = {
	"video": "📹Video",
	"audio": "🔊Audio"
}

STATUS = ("error", "fetch", "ready", "downloading", "completed")
class QueryInfo(Static):
	"""Widget to storage the information to download"""

	# __init__
	query = None
	type: str = reactive(None)
	ext: str = reactive(None)
	quality: str = reactive(None)

	title: str = reactive(None)
	uploader: str = reactive(None)
	webpage: str = reactive(None)
	url: str = reactive(None)

	status: Literal[STATUS] = reactive("wait")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		"""Auto remove when press the 'remove' button"""
		if event.button.id == "queryinfo-remove":
			self.remove()

	def watch_status(self, status: str) -> None:
		"""If 'status' variable change the QueryBox layout also will change"""
		self.query_one("#queryinfo-box").set_class((status == "fetch"), "hidden")
		self.query_one("#queryinfo-loading").set_class((status != "fetch"), "hidden")

	def update_metadata(
		self,
		title: str,
		uploader: str,
		webpage: str,
		url: str
	) -> None:
		"""Use this function to update the QueryBox metadata"""
		self.title = title
		self.uploader = uploader
		self.webpage = webpage
		self.url = url

	def compose(self) -> None:
		with Horizontal():
			# when status == "wait" start loading
			yield LoadingIndicator(id="queryinfo-loading")

			# when status != "wait" show info-box
			with Container(id="queryinfo-box"):
				# title
				yield Label(str(self.title), id="queryinfo-title")

				# metadata
				with Horizontal(id="queryinfo-meta"):
					yield Label(str(self.uploader), id="queryinfo-uploader")

				# tags
				with Horizontal(id="queryinfo-tags"):
					yield Label(MODE_TEXT[self.type], id="queryinfo-type")
					yield Label(str(self.ext), id="queryinfo-ext")
					yield Label(str(self.quality), id="queryinfo-quality")
			# remove query
			yield Button("X", id="queryinfo-remove")

		#if self.type in ("audio", "music"):
		#	self.query_one("#queryinfo-quality").add_class("hidden")

	def on_mount(self) -> None:
		self.query_one("#queryinfo-box").styles.animate("opacity", value=0.0, duration=9.0)

class Operation(Center):
	"""Main Widget to get the QueryBox settings"""
	mode = reactive(MODE["video"])

	def get_info(self) -> dict:
		"""Use this function to get the Widget information"""
		if self.mode == "video":
			return {
				"type": self.mode,
				"ext": self.query_one("#operation-video-ext").value,
				"quality": self.query_one("#operation-video-quality").value
			}
		elif self.mode in ("audio", "music"):
			return {
				"type": self.mode,
				"ext": self.query_one("#operation-audio-ext").value,
				"quality": None
			}

	def clear_select(self):
		"""For clear the values of all 'Select' Widgets"""
		self.query_one("#operation-audio-ext").value = None
		self.query_one("#operation-video-ext").value = None
		self.query_one("#operation-video-quality").value = None

	def watch_mode(self, mode: str) -> None:
		"""If 'mode' variable change, Widget also will change"""
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
				yield Label("Select a option", id="inputbox-log")
				yield Input("", placeholder="Search something...", id="inputbox-input")
				#yield Button("✅", id="inputbox-confirm")

class MediaDLApp(App):
	TITLE = "Media-DL"
	SUB_TITLE = "Start"
	CSS_PATH = "styles.css"
	BINDINGS = [
		("d", "toggle_dark", "Toggle dark mode"),
		("ctrl+d", "start_download", "Start downloads"),
		("alt+d", "test_add_query", "test query")
	]

	async def on_mount(self):
		self.query_one(Placeholder).remove()

	def compose(self) -> ComposeResult:
		yield Header()
		yield Footer()

		yield Operation()

		with Center():
			with TabbedContent("Queries", "Progress", "Console", id="output"):
				yield ScrollableContainer(Placeholder(), id="output-queries")
				yield Static("2", id="output-progress")
				yield Log(id="output-console")

	"""
	def on_button_pressed(self, event: Button.Pressed) -> None:
		button_id = event.button.id
		if button_id.startswith("opt"):
			self.opt_mode = button_id
			self.query_one("#searchbar").disabled = None
	"""

	def on_input_submitted(self, event: Input.Submitted) -> None:
		if event.input.id == "inputbox-input":
			self.action_add_query(event.input.value)

	@work(exclusive=True, exit_on_error=True)
	def extrack_ydl_info(self, url: str):
		return YDL.extrack_info(url)

	def action_add_query(
		self,
		query: str
	) -> None:

		settings: dict = self.query_one(Operation).get_info()
		item = QueryInfo()

		item.query = query
		item.type = settings["type"]
		item.ext = settings["ext"]
		item.quality = settings["quality"]

		try:
			info_json = self.extract_info(query)
			item.title = info_json["title"]
			item.uploader = info_json["uploader"]
		except:
			pass

		self.query_one("#output-queries").mount(item)
		self.query_one("#inputbox-input").value = ""
		item.scroll_visible()

	def action_enable_ui(self):
		self.query_one(Operation).disabled = None
		self.query_one("#output").disabled = None
		self.query_one(Footer).disabled = None

	def action_disable_ui(self):
		self.query_one(Operation).disabled = True
		self.query_one("#output").disabled = True
		self.query_one(Footer).disabled = True

	def action_clear_queries(self):
		for item in self.query(QueryInfo):
			item.remove()

	def action_start_download(self):
		try:
			self.action_disable_ui()
			self.process_queries()
		finally:
			#self.action_clear_queries()
			self.action_enable_ui()

	@work(exclusive=True, exit_on_error=True)
	def process_queries(self) -> None:
		queries = self.query(QueryInfo)
		worker = get_current_worker()

		console: Log = self.query_one("#output-console")

		for item in queries:
			if item.type == "video":
				dl.video(item.query, item.ext, quality=item.quality)
				if not worker.is_cancelled:
					self.call_from_thread(console.write, "COMPLETED")
			elif item.type == "audio":
				dl.audio(item.query, item.ext)
				if not worker.is_cancelled:
					self.call_from_thread(console.write, "COMPLETED")

if __name__ == "__main__":
	app = MediaDLApp()
	app.run()