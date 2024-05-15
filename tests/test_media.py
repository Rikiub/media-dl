from tempfile import TemporaryDirectory

import pytest

import media_dl
from media_dl.exceptions import ExtractError
from media_dl.models.playlist import Playlist
from media_dl.models.stream import Stream

TEMPDIR = TemporaryDirectory()


class TestExtractor:
    def test_exceptions(self):
        # Invalid URL.
        with pytest.raises(ExtractError):
            media_dl.extract_url("https://unkdown.link.com/")

        # YouTube [Private video]
        with pytest.raises(ExtractError):
            media_dl.extract_url("https://www.youtube.com/watch?v=yi50KlsCBio")

        # YouTube [Deleted video]
        with pytest.raises(ExtractError):
            media_dl.extract_url("https://www.youtube.com/watch?v=JUf1zxjR_Qw")

    def test_stream(self):
        info = media_dl.extract_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, Stream)

    def test_playlist(self):
        info = media_dl.extract_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(info, Playlist)


class TestDownloads:
    downloader = media_dl.Downloader(format="audio", quality=1, output=TEMPDIR.name)

    def test_exceptions(self):
        with pytest.raises(FileNotFoundError):
            media_dl.Downloader(ffmpeg="./unkdown_path/")

    def test_stream(self):
        # Song: Imagine Dragons - Believer
        url = "https://music.youtube.com/watch?v=Kx7B-XvmFtE"
        result = media_dl.extract_url(url)

        assert isinstance(result, Stream)

        with TEMPDIR:
            path = self.downloader.download(result)

            if not path.is_file():
                raise FileNotFoundError(path)

    def test_playlist(self):
        # Playlist: Album - HIVE (Sub Urban)
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        result = media_dl.extract_url(url)

        assert isinstance(result, Playlist)

        with TEMPDIR:
            paths = self.downloader.download_all(result)

            for path in paths:
                if not path.is_file():
                    raise FileNotFoundError(path)
