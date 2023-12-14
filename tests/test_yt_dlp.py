from tempfile import TemporaryDirectory
from pathlib import Path

import pytest
from yt_dlp import DownloadError

from media_dl.ydls import (
    YDL,
    DataInfo,
    ResultInfoList,
    PlaylistInfoList,
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
            self.ydl.search_info_from_provider(
                "https://www.youtube.com/watch?v=BaW_jenozKc", provider="NA"  # type: ignore
            )

    def test_single_url(self):
        info = self.ydl.search_info("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(info, ResultInfoList)

    def test_plalist_url(self):
        info = self.ydl.search_info(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(info, PlaylistInfoList)

    def test_custom_search(self):
        query = "Sub Urban: Album HIVE"
        limit = 5

        def check(info):
            assert isinstance(info, ResultInfoList)
            assert all(isinstance(data, DataInfo) for data in info.entries)
            assert len(info.entries) == limit

        if info := self.ydl.search_info_from_provider(
            query, provider="youtube", limit=limit
        ):
            check(info)

        if info := self.ydl.search_info_from_provider(
            query, provider="ytmusic", limit=limit
        ):
            check(info)

        if info := self.ydl.search_info_from_provider(
            query, provider="soundcloud", limit=limit
        ):
            check(info)

    def test_force_process(self):
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        if info := self.ydl.search_info(url, force_process=True):
            assert all(data.thumbnail_url for data in info.entries)


class TestDownloads:
    TEMP_PATH = TemporaryDirectory()
    TEMP_PATH = Path(TEMP_PATH.name)
    ydl = YDL(quiet=True, tempdir=TEMP_PATH, outputdir=TEMP_PATH, ext="m4a")

    def test_exceptions(self):
        # YouTube: [Private video]
        with pytest.raises(DownloadError):
            self.ydl.download_multiple(["https://www.youtube.com/watch?v=yi50KlsCBio"])

        # YouTube: [Deleted video]
        with pytest.raises(DownloadError):
            self.ydl.download_multiple(["https://www.youtube.com/watch?v=JUf1zxjR_Qw"])

    def test_multiple(self):
        urls = [
            "https://www.youtube.com/watch?v=BaW_jenozKc",
            "https://www.youtube.com/watch?v=BaW_jenozKc",
        ]
        paths = self.ydl.download_multiple(urls)
        for path in paths:
            assert path.is_file()

    def test_single(self):
        url = "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        info = self.ydl.search_info(url)

        if info:
            for item in info.entries:
                file_path = self.ydl.download_single(item)
                assert file_path.is_file()
        else:
            raise AssertionError()

    def test_search(self):
        query = "Sub Urban"

        if info := self.ydl.search_info_from_provider(query, "youtube"):
            for path in self.ydl.download_multiple([info]):
                assert path.is_file()
