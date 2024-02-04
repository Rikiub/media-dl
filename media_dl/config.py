from dataclasses import dataclass
import shutil
import atexit

from platformdirs import PlatformDirs

APPNAME = "media-dl"

dirs = PlatformDirs(APPNAME, ensure_exists=True)
DIR_DOWNLOAD = dirs.user_downloads_path / APPNAME
DIR_TEMP = dirs.site_cache_path

MAX_THREADS = 4


"""
@dataclass(slots=True)
class Main:
    output_dir: Path
    threads: int
    parse_metadata: bool


@dataclass(slots=True)
class Extensions:
    video: str
    video_quality: str
    audio: str
    audio_quality: int
"""


def clean():
    shutil.rmtree(DIR_TEMP)


atexit.register(clean)
