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
