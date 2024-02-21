from rich.console import Console
from rich.theme import Theme
from rich import traceback

__all__ = ["print", "input"]

theme = Theme(
    {
        "status.wait": "cyan",
        "status.work": "pink1",
        "status.success": "green",
        "status.warn": "orange1",
        "status.error": "red",
        "panel.queue": "blue",
        "panel.status": "blue",
        "panel.download": "blue",
        "text.label": "plum3",
        "text.desc": "misty_rose3",
        "meta.title": "misty_rose3",
        "meta.creator": "plum3",
    }
)

CONSOLE = Console(theme=theme)

traceback.install(console=CONSOLE)

print = CONSOLE.print
input = CONSOLE.input
