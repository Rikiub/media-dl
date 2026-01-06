from pathlib import Path

from media_dl.ydl.wrapper import YTDLP
from media_dl.types import InfoDict, StrPath


def run_postproces(file: Path, info: InfoDict, params: dict) -> Path:
    """Postprocess file by params."""

    info = YTDLP(params).post_process(filename=str(file), info=info)
    return Path(info["filepath"])


def parse_output_template(info: InfoDict, template: str) -> str:
    """Get a custom filename by output template."""

    return YTDLP().prepare_filename(info, outtmpl=template)


def download_thumbnail(filepath: StrPath, info: InfoDict) -> Path | None:
    ydl = YTDLP(
        {
            "writethumbnail": True,
            "outtmpl": {
                "thumbnail": "",
                "pl_thumbnail": "",
            },
        }
    )

    final = ydl._write_thumbnails(
        label=filepath, info_dict=info, filename=str(filepath)
    )

    if final:
        return Path(final[0][0])
    else:
        return None


def download_subtitle(filepath: StrPath, info: InfoDict) -> Path | None:
    ydl = YTDLP({"writesubtitles": True, "allsubtitles": True})

    subs = ydl.process_subtitles(
        filepath, info.get("subtitles"), info.get("automatic_captions")
    )
    info |= {"requested_subtitles": subs}

    final = ydl._write_subtitles(info_dict=info, filename=str(filepath))

    if final:
        return Path(final[0][0])
    else:
        return None
