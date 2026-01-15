from pathlib import Path

import pytest

from media_dl import AudioFormat, MediaDownloader, VideoFormat
from media_dl.extractor import extract_url
from media_dl.models.format.list import FormatList

URL = "https://youtube.com/watch?v=Kx7B-XvmFtE"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


def test_single(tmp_path: Path):
    result = extract_url(URL)

    assert result.type == "url"

    if result.type == "url":
        downloader = MediaDownloader("audio", quality=1, output=tmp_path)
        path = downloader.download(
            result,
            on_progress=lambda state: print(state.id),
        )

        assert path.is_file()


def test_list(tmp_path: Path):
    result = extract_url(PLAYLIST)

    assert result.type == "playlist"

    if result.type == "playlist":
        downloader = MediaDownloader("audio", quality=1, output=tmp_path)
        paths = downloader.download_all(
            result,
            on_progress=lambda state: print(state.id),
        )

        assert all(item for item in paths if item.is_file())


@pytest.fixture(scope="session")
def formats():
    result = extract_url(URL)
    assert result.type == "url"
    return result.formats


class TestFormatsFilter:
    def test_video_type(self, formats: FormatList):
        fmt = formats.only_video()
        assert all(isinstance(f, VideoFormat) for f in fmt)

    def test_audio_type(self, formats: FormatList):
        fmt = formats.only_audio()
        assert all(isinstance(f, AudioFormat) for f in fmt)

    def test_closest_quality(self, formats: FormatList):
        fmt = formats.get_closest_quality(600)
        assert fmt.quality == 720

    def test_filter(self, formats: FormatList):
        fmt = formats.filter(quality=720)
        assert all(f.quality == 720 for f in fmt)

    def test_get_by_id(self, formats: FormatList):
        ID = "137"
        fmt = formats.get_by_id(ID)
        assert fmt.id == ID
