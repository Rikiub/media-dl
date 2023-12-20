from typer import BadParameter

from media_dl.downloader.formats import FormatExt


def check_ydl_formats(fmt: str) -> str:
    if fmt in FormatExt.video.value or fmt in FormatExt.audio.value:
        return fmt
    else:
        raise BadParameter(
            f"""Invalid extension format. 
            
Avalible formats
VIDEO: {FormatExt.video.value}
AUDIO: {FormatExt.audio.value}"""
        )
