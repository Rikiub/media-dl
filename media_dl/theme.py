from rich.console import Console
from rich.theme import Theme
import rich.traceback as traceback

__all__ = ["print", "input", "console"]

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

console = Console(theme=theme)
print = console.print
input = console.input

traceback.install(console=console)
