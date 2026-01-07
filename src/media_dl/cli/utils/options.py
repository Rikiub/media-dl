from pathlib import Path
from typer import Option, Exit
from typing import Annotated

from .sections import HelpPanel


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
        rich_help_panel=HelpPanel.other,
    ),
]

VerboseOption = Annotated[
    bool,
    Option(
        "--verbose",
        help="Display more information on screen.",
        rich_help_panel=HelpPanel.other,
    ),
]

VersionOption = Annotated[
    bool,
    Option(
        "--version",
        help="Show current version and exit.",
        rich_help_panel=HelpPanel.other,
        callback=show_version,
    ),
]
