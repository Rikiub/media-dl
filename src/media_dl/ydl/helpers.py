from pathlib import Path

from media_dl.exceptions import PostProcessingError
from media_dl.types import StrPath
from media_dl.ydl.types import YDLExtractInfo, YDLParams
from media_dl.ydl.wrapper import YTDLP


def run_postproces(file: Path, info: YDLExtractInfo, params: YDLParams) -> Path:
    """Postprocess file by params."""

    info = YTDLP(params).post_process(
        filename=str(file),
        info=info,  # type: ignore
    )

    if path := info.get("filepath"):
        return Path(path)

    raise PostProcessingError("File not founded.")


def parse_output_template(info: YDLExtractInfo, template: str) -> str:
    """Get a custom filename by output template."""

    return YTDLP().prepare_filename(
        info,  # type: ignore
        outtmpl=template,
    )


def download_thumbnail(filepath: StrPath, info: YDLExtractInfo) -> Path | None:
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


def download_subtitle(filepath: StrPath, info: YDLExtractInfo) -> Path | None:
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
