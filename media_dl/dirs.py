from tempfile import mkdtemp
from pathlib import Path
import atexit
import shutil


APPNAME = "media-dl"
DIR_TEMP = Path(mkdtemp(prefix="ydl-"))


def clean():
    shutil.rmtree(DIR_TEMP)


atexit.register(clean)
