import logging

from rich.logging import RichHandler


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = ""

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

        return color + message


def init_logging(level: int | str):
    if isinstance(level, str):
        log_level = logging.getLevelName(level)
    else:
        log_level = level

    msg_format = "%(message)s"

    if log_level >= 20:
        verbose = False
    else:
        verbose = True

    rich_handler = RichHandler(
        level=log_level,
        show_level=verbose,
        show_path=verbose,
        show_time=verbose,
        markup=True,
    )
    rich_handler.setFormatter(ColorFormatter(msg_format))

    logging.basicConfig(
        level=log_level,
        format=msg_format,
        datefmt="[%X]",
        handlers=[rich_handler],
    )

    # Optimizations
    logging.logMultiprocessing = False
    logging.logProcesses = False
    logging.logThreads = False
