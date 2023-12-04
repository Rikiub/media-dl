from typer import BadParameter

from ..helper._yt_dlp import FORMAT_EXTS


def check_ydl_formats(fmt: str) -> str:
    if fmt in FORMAT_EXTS["video"] or fmt in FORMAT_EXTS["audio"]:
        return fmt
    else:
        raise BadParameter(
            f"""Invalid extension format. 
            
Avalible formats
VIDEO: {FORMAT_EXTS["video"]}
AUDIO: {FORMAT_EXTS["audio"]}"""
        )
