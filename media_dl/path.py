import atexit
import shutil
import tempfile
from os import PathLike
from pathlib import Path

# Types
StrPath = str | PathLike[str]

# Constans
DIR_TEMP = Path(tempfile.mkdtemp(prefix="ydl-"))


# Functions
def get_tempfile() -> Path:
    return Path(tempfile.mktemp(dir=DIR_TEMP))


def _clean_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(DIR_TEMP)


atexit.register(_clean_tempdir)
