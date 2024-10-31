import atexit
import os
import shutil
import tempfile
from pathlib import Path

# Constans
DIR_TEMP = Path(tempfile.mkdtemp(prefix="ydl-"))


# Functions
def get_tempfile() -> Path:
    return Path(tempfile.mktemp(dir=DIR_TEMP))


def get_global_ffmpeg() -> Path | None:
    if path := shutil.which("ffmpeg"):
        return Path(path)
    else:
        return None


def check_executable_exists(file: Path) -> bool:
    if file.is_file() and os.access(file, os.X_OK):
        return True
    else:
        return False


def _clear_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(DIR_TEMP)


atexit.register(_clear_tempdir)
