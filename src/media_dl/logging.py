import logging

from rich.logging import RichHandler

from media_dl.rich import CONSOLE
from media_dl.types import APPNAME


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        match record.levelno:
            case logging.DEBUG:
                color = "[blue]"
            case logging.INFO:
                color = "[khaki1]"
            case logging.WARNING:
                color = "[yellow][italic]"
            case logging.ERROR:
                color = "[red]"
            case logging.CRITICAL:
                color = "[bold red]"
            case _:
                color = ""

        return color + message


def init_logging(level: int):
    if level >= 20:
        verbose = False
    else:
        verbose = True

    rich_handler = RichHandler(
        level=level,
        show_level=verbose,
        show_time=verbose,
        show_path=verbose,
        markup=True,
        console=CONSOLE,
    )
    rich_handler.setFormatter(ColorFormatter())

    logging.basicConfig(
        level=level,
        datefmt="[%X]",
        handlers=[rich_handler],
    )

    # Optimizations
    logging.logMultiprocessing = False
    logging.logProcesses = False
    logging.logThreads = False


logger = logging.getLogger(APPNAME)
