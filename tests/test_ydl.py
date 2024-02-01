from tempfile import TemporaryDirectory
from pathlib import Path

import pytest

from media_dl.ydl import YDL, Media, Playlist, DownloadError

TEMPDIR = TemporaryDirectory()
TEMPPATH = Path(TEMPDIR.name)


class TestInstance:
    def test_start(self):
        YDL(output=TEMPPATH, extension="m4a")
        YDL(output=TEMPPATH, extension="m4a", quality=9)

    def test_exceptions(self):
        with pytest.raises(ValueError):
            YDL(output=TEMPPATH, extension="raw")  # type: ignore

        with pytest.raises(ValueError):
            YDL(output=TEMPPATH, extension="m4a", quality=20)  # type: ignore


class TestInfoExtractors:
    ydl = YDL(output=TEMPPATH, extension="m4a")

    def test_single_url(self):
        info = self.ydl.extract_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, Media)

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
            if isinstance(data, Media):
                self.ydl.download(data)

        # YouTube: [Deleted video]
        with pytest.raises(DownloadError):
            data = self.ydl.extract_url("https://www.youtube.com/watch?v=JUf1zxjR_Qw")
            if isinstance(data, Media):
                self.ydl.download(data)

    def test_download_single(self):
        # Song: Imagine Dragons - Believer
        url = "https://music.youtube.com/watch?v=Kx7B-XvmFtE"
        info = self.ydl.extract_url(url)

        if isinstance(info, Media):
            file_path = self.ydl.download(info)
            assert file_path.is_file()
        else:
            raise AssertionError()

    def test_download_playlist(self):
        # Playlist: Album - HIVE (Sub Urban)
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        info = self.ydl.extract_url(url)

        if isinstance(info, Playlist):
            for item in info:
                file_path = self.ydl.download(item)
                assert file_path.is_file()
        else:
            raise AssertionError()