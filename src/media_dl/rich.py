"""Custom `Rich` classes."""

from rich.console import Console, RenderableType
from rich.status import Status as _Status

CONSOLE = Console(stderr=True)


class Status(_Status):
    def __init__(self, status: RenderableType, *, disable: bool = False):
        self.disable = disable
        super().__init__(status, console=CONSOLE)

    def start(self) -> None:
        if not self.disable:
            return super().start()

    def stop(self) -> None:
        if not self.disable:
            return super().stop()


def stream_display(stream):
    """Prototipe to display pretty data on each single download."""

    # Title
    if stream.track:
        key = "Track"
        value = stream.track
    else:
        key = "Title"
        value = stream.title

    CONSOLE.print(f"[bold]{key}:[/] {value}")

    # Uploader
    if stream.artist:
        key = "Artist"
        value = stream.artist
    else:
        key = "Uploader"
        value = stream.uploader or "?"

    CONSOLE.print(f"[bold]{key}:[/] {value}")

    # Date
    if stream.datetime:
        CONSOLE.print(f"[bold]Date:[/] {stream.datetime.strftime('%d/%m/%Y')}")

    # Duration
    if stream.duration:
        total_seconds = int(stream.duration)
        seconds = total_seconds % 60
        minutes = total_seconds // 60
        hours = 0

        if minutes > 60:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

        CONSOLE.print(
            f"[bold]Duration:[/] {str(hours) + ':' if hours else ''}{minutes}:{seconds}"
        )
