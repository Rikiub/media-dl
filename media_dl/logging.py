import logging

from rich.logging import RichHandler


class LoggingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = ""

        match record.levelno:
            case logging.DEBUG:
                color = "[blue]"
            case logging.INFO:
                color = "[cyan]"
            case logging.WARNING:
                color = "[yellow]"
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
    verbose = True

    if log_level >= 20:
        verbose = False

    rich_handler = RichHandler(
        level=log_level,
        show_level=verbose,
        show_path=verbose,
        show_time=verbose,
        markup=True,
    )
    rich_handler.setFormatter(LoggingFormatter(msg_format))

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
