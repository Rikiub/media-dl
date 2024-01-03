from typing import Annotated, get_args
from dataclasses import dataclass
import concurrent.futures as cf
from threading import Event
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
from typer import Typer, Argument, Option, BadParameter

from media_dl.ydl import (
    YDL,
    Result,
    Playlist,
    DownloadError,
)
from media_dl.types import EXT_VIDEO, EXT_AUDIO
from media_dl.config import DIR_DOWNLOAD
from media_dl.theme import *

app = Typer()

SPEED = 1.5
EVENT = Event()


def check_ydl_formats(fmt: str) -> str:
    video = get_args(EXT_VIDEO)
    audio = get_args(EXT_AUDIO)

    if fmt in video or fmt in audio:
        return fmt
    else:
        raise BadParameter(
            "Invalid extension format. Avalible formats:\n"
            f"VIDEO: {', '.join(video)}\n"
            f"AUDIO: {', '.join(audio)}"
        )


@dataclass(slots=True, frozen=True)
class QueueTask:
    url: str
    task_id: TaskID


@app.command()
def download(
    url: Annotated[list[str], Argument(help="URL(s) to download", show_default=False)],
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
            min=1,
            max=9,
            help="Prefered file quality.",
        ),
    ] = 9,
    threads: Annotated[
        int,
        Option(
            "-t",
            "--threads",
            max=8,
            help="Number of threads to use when downloading.",
        ),
    ] = 3,
):
    try:
        output = output.relative_to(Path.cwd())
    except:
        pass

    ydl = YDL(
        output=output,
        extension=extension,  # type: ignore
        quality=quality,  # type: ignore
    )

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

    with Live(console=console) as live:
        # Prepare Queue UI
        url_list: list[QueueTask] = []
        for item in url:
            id = progress_queue.add_task(f"[status.wait]{item}")
            progress_queue.update(id, completed=100)
            url_list.append(QueueTask(item, id))

        print(
            Align.center(
                Group(
                    f"[text.label][bold]Extension:[/][/] [text.desc]{extension}"
                    " | "
                    f"[text.label][bold]Quality:[/][/] [text.desc]{quality}"
                    " | "
                    f"[text.label][bold]Output:[/][/] [text.desc]{output}"
                )
            )
        )

        live.update(panel_queue)

        # Main downloader used for section 3.
        def download_process(info: Result, task_id: TaskID) -> bool:
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
                if not EVENT.is_set():
                    ydl.download(info, exist_ok=False, progress_callback=progress_hook)
                    progress_download.update(
                        task_id, description="[status.success]Completed"
                    )
            except DownloadError as err:
                progress_download.update(
                    task_id, description="[status.error][bold]" + str(err.msg)
                )
                return_code = False
            except FileExistsError as err:
                progress_download.update(
                    task_id,
                    description=f'[status.warn][bold underline]"{err}"[/] already exist, ignoring',
                    completed=100,
                    total=100,
                )
            finally:
                if EVENT.is_set():
                    return_code = False
                    return return_code

                time.sleep(SPEED)
                if progress_playlist:
                    progress_playlist.advance(TaskID(0), 1)
                progress_download.remove_task(task_id)
                return return_code

        # 2. Status

        # Load UI
        for queue in url_list:
            queue_process = None

            progress_queue.reset(
                queue.task_id,
                total=None,
                description=f"[status.work][bold italic underline]{queue.url}",
            )

            try:
                queue_process = ydl.extract_url(queue.url)
                if not queue_process:
                    raise DownloadError("_")
            except DownloadError:
                progress_queue.update(
                    queue.task_id,
                    completed=100,
                    description=f"[status.error][bold strike]{queue.url}",
                )
                continue

            live.update(Group(panel_queue, panel_loading))
            time.sleep(SPEED)

            download_queue = []
            content = ()
            progress_playlist = None

            match queue_process:
                case Playlist():
                    progress_playlist = Progress(
                        TextColumn(
                            "[progress.percentage]{task.description}",
                        ),
                        MofNCompleteColumn(),
                        console=console,
                    )
                    progress_playlist.add_task(
                        "[text.label][bold]Total:[/][/]", total=queue_process.count
                    )

                    content = (
                        Group(
                            f"[text.label][bold]Title:[/][/]  [text.desc]{queue_process.title}[/]\n"
                            f"[text.label][bold]Source:[/][/] [text.desc]{queue_process.extractor}[/]",
                            HorizontalRule(),
                            progress_playlist,
                        ),
                        "Playlist",
                    )
                    download_queue = queue_process.entries
                case Result():
                    content = (
                        Group(
                            f"[text.label][bold]Title:[/][/]   [text.desc]{queue_process.title}[/]\n"
                            f"[text.label][bold]Creator:[/][/] [text.desc]{queue_process.uploader}[/]\n"
                            f"[text.label][bold]Source:[/][/]  [text.desc]{queue_process.extractor}[/]"
                        ),
                        "Item",
                    )
                    download_queue = [queue_process]
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
            for item in download_queue:
                task_id = progress_download.add_task(
                    f"[text.meta.uploader]{item.uploader}[/] - [text.meta.title]{item.title}[/]",
                    total=100,
                )
                download_list.append((item, task_id))

            live.update(Group(panel_queue, panel_status, panel_download))

            # Start Download
            with cf.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = []
                try:
                    for item, task_id in download_list:
                        future = executor.submit(download_process, item, task_id)
                        futures.append(future)
                    cf.wait(futures)
                except KeyboardInterrupt:
                    EVENT.set()

                    live.update(Group(panel_queue, "[status.error]Aborting[blink]..."))
                    cf.wait(futures)
                    live.update(Group(panel_queue, "[status.error]Aborted."))

                    raise SystemExit(1)

                success = 0
                errors = 0
                for future in futures:
                    result: bool = future.result()
                    if result:
                        success += 1
                    else:
                        errors += 1

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

        live.update(
            Group(
                panel_queue,
                Panel(
                    "[status.success][bold]Completed",
                    border_style="panel.status",
                ),
            )
        )


if __name__ == "__main__":
    app()
