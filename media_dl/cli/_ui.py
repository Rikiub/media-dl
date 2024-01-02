from typing import get_args

from typer import BadParameter

from media_dl.types import EXT_VIDEO, EXT_AUDIO


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
