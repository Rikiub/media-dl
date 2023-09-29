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

class YDLApp(App):
	TITLE = "YDL"
	CSS_PATH = "styles.tcss"
	BINDINGS = [
		("d", "toggle_dark", "Toggle dark mode")
	]

	def compose(self) -> ComposeResult:
		yield Log()