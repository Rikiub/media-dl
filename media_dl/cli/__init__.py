from media_dl.config.dirs import APPNAME
from media_dl.cli.entry import app


def run():
    app(prog_name=APPNAME.lower())
