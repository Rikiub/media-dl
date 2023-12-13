from typing import NewType, cast
from pathlib import Path
import sys

import gallery_dl.config as config
import gallery_dl.config as conf
from gallery_dl import main
from gallery_dl.job import DataJob, DownloadJob

TEMPFILE = Path("temp")
DEFAULT_CONFIG = {}

InfoDict = NewType("InfoDict", dict)


class GalleryDL:
    def __init__(self) -> None:
        config.set(("output",), "mode", "null")

    def download(self, url: str) -> bool:
        job = DownloadJob(url)
        return_code = job.run()

        if return_code == 0:
            return True
        else:
            return False

    def get_info(self, url: str) -> InfoDict | None:
        job = DataJob(url)
        return_code = job.run()

        if return_code == 0:
            return InfoDict(cast(dict, job.data))
        else:
            return None

    def test(self, url: list[str] | str, output: Path):
        with TEMPFILE.open("a") as file:
            for url in url:
                file.write(url)

        sys.argv = [
            sys.argv[0],
            "--config-ignore",
            "--filename",
            "{title}",
            "--destination",
            str(output),
            "--input-file",
            str(TEMPFILE),
        ]
        main()


if __name__ == "__main__":
    from rich import print

    gdl = GalleryDL()
    print(conf._config)
    raise SystemExit

    info = gdl.get_info("https://www.pinterest.es/rikiub_0/sheba/")
    print(info)
