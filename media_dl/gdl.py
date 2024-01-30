from dataclasses import dataclass
import contextlib
import os

from gallery_dl.exception import NoExtractorError
from gallery_dl.extractor.common import Extractor
from gallery_dl import config, extractor, job, path, formatter

from media_dl.types import Media, Playlist

config.set((), "output", "null")


@dataclass(slots=True)
class Image:
    url: str
    extractor: str
    id: str
    filename: str


@dataclass(slots=True)
class Album:
    url: str
    extractor: str


class GDL:
    def _serialize_to_dataclass(self, extractor: Extractor, info_dict: dict):
        pfmt = path.PathFormat(extractor)

        pfmt.set_directory(info_dict)
        pfmt.set_filename(info_dict)
        pfmt.build_path()
        final_path: str = pfmt.realpath

    def extract_url(self, url: str) -> list[Playlist] | Playlist | Media | None:
        """Try to get the necesary information.

        DataJob return codes:
        2: Album
        3: Image
        6: List of Albums

        Persistent info:
        - category
        - filename
        - extension
        """

        try:
            with contextlib.redirect_stdout(None):
                extr = extractor.find(url)
                if not extr:
                    return None
        except NoExtractorError:
            return None

        djob = job.DataJob(extr, file=open(os.devnull))
        djob.run()
        data: list[tuple] = djob.data

        is_album = True if (2, 6) in data[0][0] else False

        for item in data:
            print(item[0])

    def download(self, data):
        ...


if __name__ == "__main__":
    from rich import print

    url = "https://www.pinterest.es/rikiub_0/"

    gdl = GDL()
    data = gdl.extract_url(url)
    print(data)
