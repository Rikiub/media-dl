from tempfile import TemporaryDirectory
from pathlib import Path

import pytest

from media_dl import YDL
from media_dl.extractor import ExtractionError
from media_dl.types.models import Media, Playlist

TEMPPATH = Path(TemporaryDirectory().name)


class TestExtractor:
    ydl = YDL()

    def test_exceptions(self):
        with pytest.raises(ExtractionError):
            self.ydl.extract_from_url("https://unkdown.link.com")

    def test_single_url(self):
        info = self.ydl.extract_from_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, Media)

    def test_plalist_url(self):
        info = self.ydl.extract_from_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(info, Playlist)


class TestDownloads:
    ydl = YDL()

    def test_download_single(self):
        # Song: Imagine Dragons - Believer
        url = "https://music.youtube.com/watch?v=Kx7B-XvmFtE"
        info = self.ydl.extract_from_url(url)

        if isinstance(info, Media):
            file_path = self.ydl.download(info)
            # assert file_path.is_file()
        else:
            raise AssertionError()

    def test_download_playlist(self):
        # Playlist: Album - HIVE (Sub Urban)
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        info = self.ydl.extract_from_url(url)

        if isinstance(info, Playlist):
            for item in info:
                file_path = self.ydl.download(item)
                # assert file_path.is_file()
        else:
            raise AssertionError()
