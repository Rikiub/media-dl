from tempfile import mkdtemp
import atexit
import shutil

APPNAME = "media-dl"
DIR_TEMP = mkdtemp(prefix="ydl-")


def clean():
    shutil.rmtree(DIR_TEMP)


atexit.register(clean)
