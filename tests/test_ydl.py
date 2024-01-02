from tempfile import TemporaryDirectory
from pathlib import Path

import pytest

from media_dl.downloader.ydl import YDL, Result, Playlist, DownloadError

TEMPDIR = TemporaryDirectory()
TEMPPATH = Path(TEMPDIR.name)


class TestInstance:
    def test_start(self):
        YDL(output=TEMPPATH, extension="m4a")
        YDL(output=TEMPPATH, extension="m4a", quality=9)

    def test_exceptions(self):
        with pytest.raises(ValueError):
            YDL(output=TEMPPATH, extension="raw")

        with pytest.raises(ValueError):
            YDL(output=TEMPPATH, extension="m4a", quality=20)


class TestInfoExtractors:
    ydl = YDL(output=TEMPPATH, extension="m4a")

    def test_single_url(self):
        info = self.ydl.extract_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, Result)

    def test_plalist_url(self):
        info = self.ydl.extract_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(info, Playlist)


class TestDownloads:
    ydl = YDL(output=TEMPPATH, extension="m4a")

    def test_exceptions(self):
        # YouTube: [Private video]
        with pytest.raises(DownloadError):
            data = self.ydl.extract_url("https://www.youtube.com/watch?v=yi50KlsCBio")
            if isinstance(data, Result):
                self.ydl.download(data)

        # YouTube: [Deleted video]
        with pytest.raises(DownloadError):
            data = self.ydl.extract_url("https://www.youtube.com/watch?v=JUf1zxjR_Qw")
            if isinstance(data, Result):
                self.ydl.download(data)

    def test_download(self):
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        info = self.ydl.extract_url(url)

        if isinstance(info, Playlist):
            for item in info:
                file_path = self.ydl.download(item)
                assert file_path.is_file()
        else:
            raise AssertionError()
