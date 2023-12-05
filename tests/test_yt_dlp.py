from tempfile import TemporaryDirectory
from pathlib import Path

import pytest
from yt_dlp import DownloadError

from media_dl.helper._yt_dlp import (
    YDL,
    IEData,
    IEPlaylist,
    ExtTypeError,
    QualityTypeError,
)


def test_init():
    with pytest.raises(ExtTypeError):
        YDL(quiet=True, ext="raw")

    with pytest.raises(QualityTypeError):
        YDL(quiet=True, ext_quality=20)

    with pytest.raises((ExtTypeError, QualityTypeError)):
        YDL(quiet=True, ext="raw", ext_quality=20)


class TestInfoExtractors:
    ydl = YDL(quiet=True)

    def test_excetions(self):
        # Invalid Provider
        with pytest.raises(ValueError):
            self.ydl.extract_info_from_search(
                "https://www.youtube.com/watch?v=BaW_jenozKc", provider="N/A"
            )

    def test_single_url(self):
        info = self.ydl.extract_info("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, IEData)

    def test_plalist_url(self):
        info = self.ydl.extract_info(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(info, IEPlaylist)

    def test_custom_search(self):
        LIMIT = 5

        def check(info):
            assert all(isinstance(data, IEData) for data in info)
            assert len(info) == LIMIT

        if info := self.ydl.extract_info_from_search(
            "Sub Urban: Album HIVE", provider="youtube", limit=LIMIT
        ):
            check(info)

        if info := self.ydl.extract_info_from_search(
            "Sub Urban: Album HIVE", provider="ytmusic", limit=LIMIT
        ):
            check(info)

        if info := self.ydl.extract_info_from_search(
            "Sub Urban: Album HIVE", provider="soundcloud", limit=LIMIT
        ):
            check(info)


class TestDownloads:
    TEMP_PATH = TemporaryDirectory()
    TEMP_PATH = Path(TEMP_PATH.name)
    ydl = YDL(quiet=True, tempdir=TEMP_PATH, outputdir=TEMP_PATH, ext="m4a")

    def test_exceptions(self):
        # YouTube: [Private video]
        with pytest.raises(DownloadError):
            self.ydl.download_multiple("https://www.youtube.com/watch?v=yi50KlsCBio")

        # YouTube: [Deleted video]
        with pytest.raises(DownloadError):
            self.ydl.download_multiple("https://www.youtube.com/watch?v=JUf1zxjR_Qw")

    def test_syntax(self):
        if info := self.ydl.extract_info(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        ):
            for item in self.ydl.convert_info([info]):
                file_path = self.ydl.download_single(item)
                assert file_path.is_file()

    def test_url(self):
        result = self.ydl.download_multiple(
            "https://www.youtube.com/watch?v=BaW_jenozKc"
        )
        for path in result:
            assert path.is_file()

    def test_single(self):
        for item in self.ydl.convert_info(
            [
                "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
            ]
        ):
            file_path = self.ydl.download_single(item)
            assert file_path.is_file()
