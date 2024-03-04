from tempfile import TemporaryDirectory

import pytest

from media_dl import YDL
from media_dl.extractor import ExtractionError
from media_dl.models import Stream, Playlist

TEMPDIR = TemporaryDirectory()


class TestExtractor:
    ydl = YDL()

    def test_exceptions(self):
        with pytest.raises(ExtractionError):
            self.ydl.extract_url("https://unkdown.link.com")

    def test_single_url(self):
        info = self.ydl.extract_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, Stream)

    def test_plalist_url(self):
        info = self.ydl.extract_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(info, Playlist)


class TestDownloads:
    ydl = YDL(format="only-audio", output=TEMPDIR.name)

    def test_download_single(self):
        # Song: Imagine Dragons - Believer
        url = "https://music.youtube.com/watch?v=Kx7B-XvmFtE"
        stream = self.ydl.extract_url(url)

        if isinstance(stream, Stream):
            with TEMPDIR:
                self.ydl.download(stream)
        else:
            raise AssertionError(stream)

    def test_download_playlist(self):
        # Playlist: Album - HIVE (Sub Urban)
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        playlist = self.ydl.extract_url(url)

        if isinstance(playlist, Playlist):
            with TEMPDIR:
                self.ydl.download(playlist)
        else:
            raise AssertionError(playlist)
