from dataclasses import dataclass
import concurrent.futures as cf
from typing import Annotated
from pathlib import Path
import time

from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.table import Column
from rich.console import Group
from rich.markdown import HorizontalRule
from rich.progress import (
    MofNCompleteColumn,
    DownloadColumn,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    Progress,
    TaskID,
)
from typer import Typer, Argument, Option

from ..ydls import (
    YDL,
    QUALITY,
    DataInfo,
    PlaylistInfoList,
    ResultInfoList,
    DownloadError,
)
from ..config import DIR_DOWNLOAD, DIR_TEMP
from ._ui import check_ydl_formats
from ..theme import *

app = Typer()

SPEED = 1.5


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

    try:
        output = output.relative_to(Path.cwd())
    except:
        pass

    ydl = YDL(
        quiet=True,
        tempdir=DIR_TEMP,
        outputdir=output,
        ext=extension,
        ext_quality=quality,
    )

    with Live(console=console) as live:
        # Main UI Components
        progress_queue = Progress(
            SpinnerColumn(),
            TextColumn(
                "[progress.description]{task.description}",
                table_column=Column(justify="right"),
            ),
            console=console,
        )
        panel_queue = Align.center(
            Panel(
                Group(
                    Align.center(
                        f"[text.label][bold]Output:[/][/] [text.desc]{output}[/]"
                    ),
                    Align.center(
                        f"[text.label][bold]Extension:[/][/] [text.desc]{extension}[/] | [text.label][bold]Quality:[/][/] [text.desc]{quality}[/]"
                    ),
                    HorizontalRule(),
                    progress_queue,
                ),
                title="Downloads",
                width=100,
                padding=(0, 2),
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
                table_column=Column(
                    justify="left",
                    width=40,
                    no_wrap=True,
                    overflow="ellipsis",
                ),
            ),
            BarColumn(table_column=Column(justify="center", width=20)),
            DownloadColumn(table_column=Column(justify="right", width=15)),
            transient=True,
            expand=True,
            console=console,
        )
        panel_download = Panel(progress_download, border_style="panel.download")

        # Prepare Queue UI
        url_list: list[tuple] = []
        for url in urls:
            queue_task_id = progress_queue.add_task(f"[status.work]{url}")
            url_list.append((url, queue_task_id))

        live.update(panel_queue)

        @dataclass(slots=True)
        class QueueTask:
            url: str
            item: ResultInfoList
            task_id: TaskID

        # 1. Queue list
        item_list: list[QueueTask] = []
        for task in url_list:
            url, queue_task_id = task

            try:
                if queue_item := ydl.search_info(url):
                    progress_queue.update(
                        queue_task_id, completed=100, description=f"[status.wait]{url}"
                    )
                    item_list.append(
                        QueueTask(url=url, item=queue_item, task_id=queue_task_id)
                    )
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
        def download_process(info: DataInfo, task_id: TaskID) -> bool:
            return_code = True

            def progress_hook(d):
                match d["status"]:
                    case "downloading":
                        total_bytes = d.get("total_bytes") or d.get(
                            "total_bytes_estimate"
                        )
                        progress_download.update(
                            task_id, completed=d["downloaded_bytes"], total=total_bytes
                        )
                    case "finished":
                        progress_download.update(
                            task_id, description="[status.wait][bold]Converting"
                        )

            try:
                ydl.download_single(
                    info,
                    exist_ok=False,
                    progress=[lambda d: progress_hook(d)],
                )
                progress_download.update(
                    task_id, description="[status.success]Completed"
                )
            except DownloadError as err:
                progress_download.update(
                    task_id, description="[status.error][bold]" + str(err.msg)
                )
                return_code = False
            except FileExistsError as e:
                progress_download.update(
                    task_id,
                    description=f'[status.warn][bold underline]"{e}"[/] already exist, ignoring',
                    completed=100,
                    total=100,
                )
            finally:
                time.sleep(SPEED)
                if progress_playlist:
                    progress_playlist.advance(TaskID(0), 1)
                progress_download.remove_task(task_id)
                return return_code

        # 2. Status
        @dataclass(slots=True)
        class ErrorReport:
            name: str
            success: int
            errors: int

        error_list: list[ErrorReport] = []

        # Load UI
        for queue in item_list:
            live.update(Group(panel_queue, panel_loading))
            time.sleep(SPEED)
            progress_queue.reset(
                queue.task_id,
                description=f"[status.work][bold italic underline]{queue.url}",
                total=None,
            )

            aux_downloads = []
            content = ()
            progress_playlist = None

            match queue.item:
                case PlaylistInfoList():
                    progress_playlist = Progress(
                        TextColumn(
                            "[progress.percentage]{task.description}",
                        ),
                        MofNCompleteColumn(),
                        console=console,
                    )
                    progress_playlist.add_task(
                        "[text.label][bold]Total:[/][/]", total=queue.item.total_count
                    )

                    content = (
                        Group(
                            f"[text.label][bold]Title:[/][/]  [text.desc]{queue.item.title}[/]\n"
                            f"[text.label][bold]Source:[/][/] [text.desc]{queue.item.extractor}[/]",
                            HorizontalRule(),
                            progress_playlist,
                        ),
                        "Playlist",
                    )
                    aux_downloads = queue.item.entries
                case ResultInfoList():
                    item = queue.item.entries[0]
                    content = (
                        Group(
                            f"[text.label][bold]Title:[/][/]   [text.desc]{item.title}[/]\n"
                            f"[text.label][bold]Creator:[/][/] [text.desc]{item.creator}[/]\n"
                            f"[text.label][bold]Source:[/][/]  [text.desc]{item.extractor}[/]"
                        ),
                        "Item",
                    )
                    aux_downloads = [item]
                case _:
                    raise ValueError()

            text, title = content
            panel_status = Panel(
                text,
                padding=(1, 3),
                width=75,
                expand=False,
                border_style="panel.status",
            )
            panel_status.title = title
            panel_status = Align.center(panel_status)

            # 3. Downloader

            # Prepare Downloader UI
            download_list = []
            for item in aux_downloads:
                task_id = progress_download.add_task(
                    f"[text.meta.creator]{item.creator}[/] - [text.meta.title]{item.title}[/]",
                    total=None,
                )
                download_list.append((item, task_id))

            live.update(Group(panel_queue, panel_status, panel_download))

            # Start Download
            with cf.ThreadPoolExecutor(max_workers=threads) as executor:
                try:
                    futures = []
                    for item, task_id in download_list:
                        future = executor.submit(download_process, item, task_id)
                        futures.append(future)
                    cf.wait(futures)
                except KeyboardInterrupt:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise SystemExit(1)

                success = 0
                errors = 0
                for future in futures:
                    result: bool = future.result()
                    if result:
                        success += 1
                    else:
                        errors += 1

                error_list.append(
                    ErrorReport(name=queue.url, success=success, errors=errors)
                )

            if errors >= 1:
                queue_status = f"[status.warn][bold]({errors})"
            else:
                queue_status = ""

            # Update current Queue status
            progress_queue.update(
                queue.task_id,
                completed=100,
                description=f"[status.success][bold strike]{queue.url}[/][/] "
                + queue_status,
            )

        # 3. All tasks completed
        errors_pretty = []
        for report in error_list:
            if report.errors >= 1:
                errors_pretty.append(
                    f"[status.warn]Catched [status.warn][bold]({report.errors})[/][/] errors in [text.meta.title][bold underline]{report.name}"
                )

        live.update(
            Group(
                panel_queue,
                Panel(
                    Group(
                        "[status.success][bold]Completed\n",
                        *errors_pretty,
                    ),
                    border_style="panel.status",
                ),
            )
        )


if __name__ == "__main__":
    app()
