from typing import Annotated, Literal, get_args
from pathlib import Path
import sys

from typer import Typer, Argument, Option
from strenum import StrEnum

from media_dl import YDL, DownloadConfig
from media_dl.extractor import ExtractionError
from media_dl.types.formats import FormatTuples, SEARCH_PROVIDER, EXTENSION
from media_dl.config.theme import *

app = Typer(rich_markup_mode="rich")

Format = StrEnum("Format", FormatTuples.format)
Provider = StrEnum("Provider", get_args(Literal[SEARCH_PROVIDER, "url"]))
Extension = StrEnum("Extension", get_args(Literal[EXTENSION, "disabled"]))


class HelpPanel(StrEnum):
    required = "Required"
    formatting = "Formatting"
    search = "Search"
    convert = "Conversion (Advanced)"
    other = "Others (Advanced)"


@app.command(name="download", no_args_is_help=True)
def download(
    query: Annotated[
        list[str],
        Argument(
            help="[green]URL(s)[/] or [green]text[/] to process and download.",
            show_default=False,
        ),
    ],
    format: Annotated[
        Format,
        Option(
            "--format",
            "-f",
            help="File type to request. Would fallback to [green]🎵'audio'[/] if [green]📹'video'[/] is not available.",
            prompt="What format you want?",
            rich_help_panel=HelpPanel.required,
            show_default=False,
        ),
    ],
    search: Annotated[
        Provider,
        Option(
            "--search-from",
            "-s",
            help="Switch to [green]'search'[/] mode from selected provider.",
            rich_help_panel=HelpPanel.formatting,
        ),
    ] = "url",  # type: ignore
    video_res: Annotated[
        str,
        Option(
            "--video-quality",
            "-r",
            help="Prefered video resolution. If selected quality is'nt available, closest one is used instead.",
            rich_help_panel=HelpPanel.formatting,
            min=1,
            max=9,
        ),
    ] = "720",
    output: Annotated[
        Path,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            rich_help_panel=HelpPanel.formatting,
            file_okay=False,
            resolve_path=True,
            show_default=False,
        ),
    ] = Path.cwd(),
    convert: Annotated[
        Extension,
        Option(
            "--convert-to",
            help="Convert final file to wanted extension (Slow process).",
            rich_help_panel=HelpPanel.convert,
        ),
    ] = "disabled",  # type: ignore
    audio_quality: Annotated[
        int,
        Option(
            "--audio-quality",
            help="Prefered audio quality when do a file conversion.",
            rich_help_panel=HelpPanel.convert,
            min=1,
            max=9,
        ),
    ] = 9,
    threads: Annotated[
        int,
        Option(
            "--threads", help="Max process to execute.", rich_help_panel=HelpPanel.other
        ),
    ] = 4,
    debug: Annotated[
        bool,
        Option("--debug", help="Enable debug mode.", rich_help_panel=HelpPanel.other),
    ] = False,
):
    """[green]yt-dlp[/] helper with [italic green]nice defaults[/] ✨."""

    if not debug:
        sys.tracebacklimit = 0

    ydl = YDL()
    config = DownloadConfig(
        format=format,  # type: ignore
        convert_to=convert if convert != "disabled" else None,  # type: ignore
        video_res=int(video_res),
        audio_quality=int(audio_quality) if audio_quality != 9 else 9,
        output=output,
    )

    for url in query:
        print(f"[status.work][Processing]: [green]'{url}'")

        try:
            if search != "url":
                info = ydl.extract_from_search(url, search)  # type: ignore
                info = info[0]
            else:
                info = ydl.extract_from_url(url)

            if not info:
                raise ExtractionError()
        except ExtractionError:
            print(f"[status.work][Error]: [green]'{url}'[/] is invalid or unsupported.")
            continue

        ydl.download(info, config=config)
        print(f"[status.work][Done]: {url}")
