from tempfile import TemporaryDirectory

import pytest

from media_dl import AudioFormat, Media, MediaDownloader, Playlist, VideoFormat
from media_dl.models.formats.list import FormatList

try:
    from rich import print

    pprint = print
except ImportError:
    from pprint import pprint as _pprint

    pprint = _pprint


TEMPDIR = TemporaryDirectory()

URL = "https://youtube.com/watch?v=Kx7B-XvmFtE"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


def test_simple():
    with TEMPDIR:
        media = Media.from_url(URL)

        downloader = MediaDownloader("audio", quality=1, output=TEMPDIR.name)
        path = downloader.download_all(media)

        pprint(path)


def test_advanced():
    with TEMPDIR:
        downloader = MediaDownloader("audio", quality=1, output=TEMPDIR.name)

        try:
            result = Media.from_url(URL)
            paths = downloader.download(
                result,
                on_progress=lambda *args: pprint(*args),
            )
        except TypeError:
            result = Playlist.from_url(PLAYLIST)
            paths = downloader.download_all(result)

        pprint(paths)


@pytest.fixture(scope="session")
def formats():
    return Media.from_url(URL).formats


class TestFormatsFilter:
    def test_video_type(self, formats: FormatList):
        fmt = formats.only_video()
        assert all(isinstance(f, VideoFormat) for f in fmt)
        pprint("VIDEOS:")
        pprint(fmt)

    def test_audio_type(self, formats: FormatList):
        fmt = formats.only_audio()
        assert all(isinstance(f, AudioFormat) for f in fmt)
        pprint("AUDIOS:")
        pprint(fmt)

    def test_closest_quality(self, formats: FormatList):
        fmt = formats.get_closest_quality(600)
        assert fmt.quality == 720

    def test_get_by_id(self, formats: FormatList):
        ID = "137"
        fmt = formats.get_by_id(ID)
        assert fmt.id == ID
        pprint("BY ID:")
        pprint(fmt)
