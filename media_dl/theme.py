from rich.console import Console
from rich.theme import Theme

__all__ = ["print", "input", "console"]

theme = Theme(
    {
        "status.wait": "cyan",
        "status.work": "pink1",
        "status.success": "green",
        "status.warn": "orange1",
        "status.error": "red",
        "panel.queue": "yellow",
        "panel.status": "blue",
        "panel.download": "blue",
        "downloader.title": "yellow",
        "downloader.creator": "green",
        "text.label": "honeydew2 bold",
        "text.desc": "pink1",
    }
)
console = Console(theme=theme)

print = console.print
input = console.input
