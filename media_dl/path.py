import atexit
import os
import shutil
import tempfile
from pathlib import Path

# Constants
TEMP_DIR = Path(tempfile.mkdtemp(prefix="ydl-"))


# Functions
def get_tempfile() -> Path:
    return Path(tempfile.mktemp(dir=TEMP_DIR))


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

    shutil.rmtree(TEMP_DIR)


atexit.register(_clear_tempdir)
