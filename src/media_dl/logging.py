import logging
from typing import Literal

from loguru import logger
from rich.logging import RichHandler

from media_dl.rich import CONSOLE

LOGGING_LEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


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


def init_logging(level: LOGGING_LEVELS):
    if level == "INFO":
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

    logger.remove()
    logger.add(
        rich_handler,
        level=level,
        format="{message}",
        backtrace=False,
    )

    logger.enable("media_dl")
