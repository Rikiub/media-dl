from enum import Enum
from typing import Annotated
from typer import Typer, Argument, Option

app = Typer()


class Provider(Enum):
    ytmusic = "ytmusic"
    soundcloud = "soundcloud"


@app.command()
def search(
    query: Annotated[str, Argument(help="Search term")],
    provider: Annotated[
        Provider, Option("--provider", "-p", show_default=False)
    ] = Provider.ytmusic,
):
    ...
