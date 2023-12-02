import concurrent.futures as cf
from typing import Annotated
from pathlib import Path
import time

from rich.live import Live
from rich.align import Align
from rich.panel import Panel
from rich.console import Group
from rich.progress import (
    TransferSpeedColumn,
    MofNCompleteColumn,
    DownloadColumn,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    Progress,
    TaskID,
)
from typer import Typer, Argument, Option

from ..helper._yt_dlp import (
    YDL,
    QUALITY,
    IEData,
    IEPlaylist,
    DownloadError,
)
from ..config import DIR_DOWNLOAD, DIR_CACHE
from ._ui import check_ydl_formats
from ..theme import *

app = Typer()
SPEED = 1.5
PROGRESS_OVERFLOW_LIMIT = 100


@app.command()
def download(
    urls: Annotated[list[str], Argument(help="URL to download", show_default=False)],
    output: Annotated[
        Path,
        Option(
            "-o",
            "--output",
            help="Directory where to save downloads.",
            file_okay=False,
            resolve_path=True,
        ),
    ] = DIR_DOWNLOAD,
    extension: Annotated[
        str,
        Option(
            "-x",
            "--extension",
            help="Prefered file extension.",
            callback=check_ydl_formats,
        ),
    ] = "mp4",
    quality: Annotated[
        int,
        Option(
            "-q",
            "--quality",
            min=0,
            max=len(QUALITY),
            clamp=True,
            help="Prefered file quality.",
        ),
    ] = 9,
    threads: Annotated[
        int,
        Option(
            "-t",
            "--threads",
            max=8,
            clamp=True,
            help="Number of threads to use when downloading.",
        ),
    ] = 3,
    no_metadata: Annotated[
        bool,
        Option(
            "-m",
            "--no-metadata",
            help="Disable embeding music metadata in audio files if URL are avalaible.",
        ),
    ] = False,
):
    if no_metadata:
        no_metadata = not False

    ydl = YDL(quiet=True, cachedir=DIR_CACHE)

    with Live(console=console) as live:
        # Main UI Components
        progress_queue = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        panel_queue = Align.center(
            Panel(
                progress_queue,
                title="Downloads",
                expand=False,
                border_style="panel.queue",
            )
        )

        progress_loading = Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        )
        progress_loading.add_task(f"[status.work]Loading[blink]...[/]")
        panel_loading = Align.center(
            Panel(progress_loading, border_style="panel.status", expand=False)
        )

        progress_download = Progress(
            TextColumn(
                "[progress.percentage]{task.description}",
            ),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            expand=True,
            console=console,
        )
        panel_download = Panel(progress_download, border_style="panel.download")

        # Prepare Queue UI
        url_list = []
        for url in urls:
            queue_task_id = progress_queue.add_task(f"[status.work]{url}")
            url_list.append((url, queue_task_id))

        live.update(panel_queue)

        # 1. Task list
        item_list = []
        for task in url_list:
            url, queue_task_id = task

            try:
                if queue_item := ydl.extract_info(url):
                    progress_queue.update(
                        queue_task_id, completed=100, description=f"[status.wait]{url}"
                    )
                    item_list.append((queue_item, queue_task_id))
                else:
                    raise DownloadError("Failed to fetch data")
            except DownloadError:
                progress_queue.update(
                    queue_task_id, completed=100, description=f"[status.error]{url}"
                )

        if not item_list:
            live.update(Group(panel_queue, Panel("Too many errors to continue")))
            raise SystemExit(1)

        # Main downloader used for section 3.
        def download_process(info: IEData, extension: str, output: Path, id: TaskID):
            def progress_hook(d, task_id):
                if d["status"] == "downloading":
                    total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                    progress_download.update(
                        task_id, completed=d["downloaded_bytes"], total=total_bytes
                    )

            try:
                ydl.download(
                    info,
                    extension,
                    quality,
                    output=output,
                    exist_ok=False,
                    progress=[lambda d: progress_hook(d, id)],
                )
                progress_download.update(id, description="[status.success]Completed")
            except DownloadError as e:
                text = str(e)[:PROGRESS_OVERFLOW_LIMIT] + "..."
                progress_download.update(id, description=f"[status.error]{text}")
            except FileExistsError as e:
                text = f'[status.warn][bold underline]"{e}"[/] already exist, ignoring'
                text = text[:PROGRESS_OVERFLOW_LIMIT] + "..."
                progress_download.update(id, description=text)
            finally:
                time.sleep(SPEED)
                if progress_playlist:
                    task_id = progress_playlist.task_ids[0]
                    progress_playlist.advance(task_id, 1)
                progress_download.remove_task(id)

        # 2. Status

        # Load UI
        content = ()
        progress_playlist = None

        for queue_item, queue_task_id in item_list:
            live.update(Group(panel_queue, panel_loading))
            time.sleep(SPEED)

            progress_queue.reset(
                queue_task_id,
                description=f"[status.work][bold italic underline]{queue_item.url}",
                total=None,
            )

            ie_items = []

            if isinstance(queue_item, IEData):
                content = (
                    Group(
                        f"[text.label]Title:[/]     [text.desc]{queue_item.title}[/]\n"
                        f"[text.label]Creator:[/]   [text.desc]{queue_item.creator}[/]\n"
                        f"[text.label]Extractor:[/] [text.desc]{queue_item.extractor}[/]\n"
                        f"[text.label]URL:[/]       [text.desc][underline]{queue_item.url}[/]"
                    ),
                    "Item",
                )
                ie_items = [queue_item]

            elif isinstance(queue_item, IEPlaylist):
                progress_playlist = Progress(
                    TextColumn(
                        "[progress.percentage]{task.description}",
                    ),
                    MofNCompleteColumn(),
                    console=console,
                )

                content = (
                    Group(
                        f"[text.label]Title:[/]     [text.desc]{queue_item.title}[/]\n"
                        f"[text.label]Extractor:[/] [text.desc]{queue_item.extractor}[/]\n"
                        f"[text.label]URL:[/]       [text.desc][underline]{queue_item.url}[/]\n",
                        progress_playlist,
                    ),
                    "Playlist",
                )

                progress_playlist.add_task(
                    "[text.label]Total:[/]", total=queue_item.total_count
                )
                ie_items = queue_item.ie_list
            else:
                raise ValueError()

            text, title = content
            panel_status = Panel(
                text,
                expand=False,
                padding=(1, 3),
                border_style="panel.status",
            )
            panel_status.title = title
            panel_status = Align.center(panel_status)

            # 3. Downloader

            # Prepare Downloader UI
            downloads = []
            for item in ie_items:
                id = progress_download.add_task(
                    f"[downloader.creator]{item.creator}[/] - [downloader.title]{item.title}[/]",
                    total=None,
                )
                downloads.append((item, id))

            live.update(Group(panel_queue, panel_status, panel_download))

            # Start Download
            with cf.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = []
                for item, task_id in downloads:
                    future = executor.submit(
                        download_process, item, extension, output, task_id
                    )
                    futures.append(future)
                cf.wait(futures)

            # Update current Queue status
            progress_queue.update(
                queue_task_id,
                completed=100,
                description=f"[status.success][bold strike]{queue_item.url}",
            )

        # 3. All tasks completed
        live.update(
            Group(
                panel_queue,
                Panel("[status.success][bold]Completed!", border_style="panel.status"),
            )
        )


if __name__ == "__main__":
    app()
