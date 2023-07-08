from rich.console import Console
from rich.themes import Theme
from rich.traceback import install

theme = Theme({
    "error": "bold red",
    "warning": "red",

    "high": "bold yellow",
    "low": "bold italic cyan"
})
console = Console(theme=theme)

print = console.print
input = console.input

# install rich traceback
install(show_locals=True)