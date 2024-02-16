from typing import Annotated, Literal, get_args
from pathlib import Path
import sys

from typer import Typer, Argument, Option
from strenum import StrEnum
from media_dl.downloader import DownloaderError

from media_dl.types.formats import SEARCH_PROVIDER, EXTENSION, FORMAT
from media_dl.extractor import ExtractionError
from media_dl import YDL, DownloadConfig
from media_dl.config.theme import print
from media_dl.config.dirs import APPNAME

app = Typer(rich_markup_mode="markdown")

Format = StrEnum("Format", get_args(FORMAT))
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
            help="**URL** or **Query** to process and download.",
            show_default=False,
        ),
    ],
    format: Annotated[
        Format,
        Option(
            "--format",
            "-f",
            help="File type to request. Would fallback to **audio** if **video** is not available.",
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
            help="Switch to **search** mode from selected provider.",
            rich_help_panel=HelpPanel.formatting,
        ),
    ] = Provider["url"],
    video_res: Annotated[
        int,
        Option(
            "--video-quality",
            "-r",
            help="Prefered video resolution. If selected **quality** is'nt available, closest one is used instead.",
            rich_help_panel=HelpPanel.formatting,
        ),
    ] = 720,
    output: Annotated[
        Path,
        Option(
            "--output",
            "-o",
            help="Directory where to save downloads.",
            rich_help_panel=HelpPanel.formatting,
            show_default=False,
            file_okay=False,
            resolve_path=True,
        ),
    ] = Path.cwd(),
    convert: Annotated[
        Extension,
        Option(
            "--convert-to",
            help="Convert final file to wanted extension (Slow process).",
            rich_help_panel=HelpPanel.convert,
        ),
    ] = Extension["disabled"],
    audio_quality: Annotated[
        int,
        Option(
            "--audio-quality",
            help="Prefered **audio quality** when do a file conversion. Can be range between **[0-9]** or audio bitrate **[128-360]**",
            rich_help_panel=HelpPanel.convert,
        ),
    ] = 9,
    threads: Annotated[
        int,
        Option(
            "--threads",
            help="Max parallel process to execute.",
            rich_help_panel=HelpPanel.other,
        ),
    ] = 4,
    debug: Annotated[
        bool,
        Option(
            "--debug",
            help="Enable debug mode and tracebacks.",
            rich_help_panel=HelpPanel.other,
        ),
    ] = False,
):
    """**yt-dlp** helper with ***nice defaults*** ✨."""

    if not debug:
        sys.tracebacklimit = 0

    ydl = YDL(
        config=DownloadConfig(
            format=format.value,
            convert_to=convert.value if convert != "disabled" else None,
            video_quality=video_res,
            audio_quality=audio_quality,
            output=output,
        ),
        threads=threads,
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
                raise ExtractionError(f"'{url}' is invalid or unsupported.")

            ydl.download(info)
        except ExtractionError as err:
            print(f"[status.work][Error]: {err}")
            continue
        except DownloaderError as err:
            print(f"[status.work][Error]: [status.error]{err}")
        else:
            print(f"[status.work][Done]: {url}")


def run():
    app(prog_name=APPNAME.lower())


if __name__ == "__main__":
    run()
