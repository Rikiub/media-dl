from typing import Annotated
from pathlib import Path

from typer import Option

Output = Annotated[
    Path,
    Option(
        "-o",
        "--output",
        help="Directory where to save downloads.",
        file_okay=False,
        resolve_path=True,
    ),
]
