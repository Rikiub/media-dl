from pathlib import Path
from typing import cast

from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import DownloadError as YDLDownloadError

from media_dl.exceptions import DownloadError, ExtractError, PostProcessingError
from media_dl.types import StrPath
from media_dl.ydl.messages import format_except_message
from media_dl.ydl.types import YDLExtractInfo, YDLParams
from media_dl.ydl.wrapper import YTDLP


def extract_info(query: str) -> YDLExtractInfo:
    try:
        ydl = YTDLP(
            {
                "extract_flat": "in_playlist",
                "skip_download": True,
            }
        )
        info = ydl.extract_info(query, download=False)
        return cast(YDLExtractInfo, info)
    except (YDLDownloadError, RequestError) as err:
        msg = format_except_message(err)
        raise ExtractError(msg)


def download_from_info(info: YDLExtractInfo, params: YDLParams) -> Path:
    retries: YDLParams = {"retries": 0, "fragment_retries": 0}

    try:
        result = YTDLP(retries | params).process_ie_result(
            info,  # type: ignore
            download=True,
        )
        filepath = result["requested_downloads"][0]["filepath"]  # type: ignore
        return Path(filepath)
    except YDLDownloadError as err:
        msg = format_except_message(err)

        if "Postprocessing:" in msg:
            raise PostProcessingError(msg)
        else:
            raise DownloadError(msg)


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


def download_subtitles(filepath: StrPath, info: YDLExtractInfo) -> list[Path] | None:
    ydl = YTDLP({"writesubtitles": True, "allsubtitles": True})

    subs = ydl.process_subtitles(
        str(filepath),
        info.get("subtitles", {}),
        info.get("automatic_captions", {}),
    )
    info |= {"requested_subtitles": subs}  # type: ignore

    final: list[tuple[str, str]] = ydl._write_subtitles(  # type: ignore
        info_dict=info,
        filename=str(filepath),
    )

    if final:
        result = [Path(entry[0]) for entry in final]
        return result
    else:
        return None
