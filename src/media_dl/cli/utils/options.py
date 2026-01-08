from pathlib import Path
from typer import Option, Exit
from typing import Annotated


def show_version(show: bool) -> None:
    if show:
        from importlib.metadata import version

        print(version(Path(__file__).parent.parent.parent.name))

        raise Exit()


QuietOption = Annotated[
    bool,
    Option(
        "--quiet",
        help="Supress screen information.",
    ),
]

VerboseOption = Annotated[
    bool,
    Option(
        "--verbose",
        help="Display more information on screen.",
    ),
]

VersionOption = Annotated[
    bool,
    Option(
        "--version",
        help="Show current version and exit.",
        callback=show_version,
    ),
]
