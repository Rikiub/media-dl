import atexit
import shutil
import tempfile
from os import PathLike
from pathlib import Path

# Constans
DIR_TEMP = Path(tempfile.mkdtemp(prefix="ydl-"))

StrPath = str | PathLike[str]


# Functions
def get_tempfile() -> Path:
    return Path(tempfile.mktemp())


def _clean_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(DIR_TEMP)


atexit.register(_clean_tempdir)
