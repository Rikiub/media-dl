from tempfile import TemporaryDirectory

import pytest

import media_dl
from media_dl.models import Stream, Playlist
from media_dl.exceptions import ExtractError, DownloadError

TEMPDIR = TemporaryDirectory()


class TestExtractor:
    def test_exceptions(self):
        with pytest.raises(ExtractError):
            media_dl.extract_url("https://unkdown.link.com/")

        # YouTube [Private video]
        with pytest.raises(ExtractError):
            result = media_dl.extract_url("https://www.youtube.com/watch?v=yi50KlsCBio")

        # YouTube [Deleted video]
        with pytest.raises(ExtractError):
            result = media_dl.extract_url("https://www.youtube.com/watch?v=JUf1zxjR_Qw")

    def test_single_url(self):
        info = media_dl.extract_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, Stream)

    def test_plalist_url(self):
        info = media_dl.extract_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(info, Playlist)


class TestDownloads:
    downloader = media_dl.Downloader(format="audio", quality=1, output=TEMPDIR.name)

    def test_download_single(self):
        # Song: Imagine Dragons - Believer
        url = "https://music.youtube.com/watch?v=Kx7B-XvmFtE"
        stream = media_dl.extract_url(url)

        if isinstance(stream, Stream):
            with TEMPDIR:
                path = self.downloader.download_single(stream)

                if not path.is_file():
                    raise FileNotFoundError(path)
        else:
            raise AssertionError(stream)

    def test_download_playlist(self):
        # Playlist: Album - HIVE (Sub Urban)
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        playlist = media_dl.extract_url(url)

        if isinstance(playlist, Playlist):
            with TEMPDIR:
                paths = self.downloader.download_multiple(playlist)
                p = paths[0]

                if not p.is_file():
                    raise FileNotFoundError(p)
        else:
            raise AssertionError(playlist)
