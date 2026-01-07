from pathlib import Path

from media_dl.exceptions import PostProcessingError
from media_dl.types import StrPath
from media_dl.ydl.types import InfoDict, YDLParams
from media_dl.ydl.wrapper import YTDLP


def run_postproces(file: Path, info: InfoDict, params: YDLParams) -> Path:
    """Postprocess file by params."""

    info = YTDLP(params).post_process(
        filename=str(file),
        info=info,  # type: ignore
    )

    if path := info.get("filepath"):
        return Path(path)

    raise PostProcessingError("File not founded.")


def parse_output_template(info: InfoDict, template: str) -> str:
    """Get a custom filename by output template."""

    return YTDLP().prepare_filename(
        info,  # type: ignore
        outtmpl=template,
    )


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

    final = ydl._write_thumbnails(  # type: ignore
        label=filepath,
        info_dict=info,
        filename=str(filepath),
    )

    if final:
        return Path(final[0][0])
    else:
        return None


def download_subtitle(filepath: StrPath, info: InfoDict) -> Path | None:
    ydl = YTDLP({"writesubtitles": True, "allsubtitles": True})

    subs = ydl.process_subtitles(
        str(filepath),
        info.get("subtitles", {}),
        info.get("automatic_captions", {}),
    )
    info |= {"requested_subtitles": subs}  # type: ignore

    final = ydl._write_subtitles(  # type: ignore
        info_dict=info,
        filename=str(filepath),
    )

    if final:
        return Path(final[0][0])
    else:
        return None
