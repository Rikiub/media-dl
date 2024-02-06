from dataclasses import dataclass
from pathlib import Path
import shutil
import atexit
from typing import Literal

from platformdirs import PlatformDirs

from media_dl.types import EXT_AUDIO, EXT_VIDEO, VIDEO_RES

APPNAME = "media-dl"

dirs = PlatformDirs(APPNAME, ensure_exists=True)
DIR_DOWNLOAD = dirs.user_downloads_path / APPNAME
DIR_TEMP = dirs.site_cache_path


@dataclass(slots=True)
class GeneralConf:
    output: Path
    threads: int
    pref_res: VIDEO_RES


@dataclass(slots=True)
class ConvertConf:
    status: Literal["auto", "always", "never"]
    video: EXT_VIDEO
    audio: EXT_AUDIO


def clean():
    shutil.rmtree(DIR_TEMP)


atexit.register(clean)
