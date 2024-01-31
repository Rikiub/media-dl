from tempfile import TemporaryDirectory
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APPNAME = "media-dl"

dirs = PlatformDirs(APPNAME, ensure_exists=True)
DIR_DOWNLOAD = dirs.user_downloads_path / APPNAME
DIR_TEMP = TemporaryDirectory()
DIR_TEMP = Path(DIR_TEMP.name)


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
