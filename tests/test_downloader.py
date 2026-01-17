from pathlib import Path

import pytest

from media_dl.downloader.main import MediaDownloader
from media_dl.extractor import MediaExtractor


@pytest.fixture
def download(tmp_path: Path):
    def _wrap(url: str):
        extractor = MediaExtractor(use_cache=False)
        result = extractor.extract_url(url)

        paths = MediaDownloader(
            quality=1,
            output=tmp_path,
            extractor=extractor,
        ).download_all(result)

        assert len(paths) >= 1

        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(path)

    return _wrap


def test_media(download):
    download("https://youtube.com/watch?v=Kx7B-XvmFtE")


def test_playlist(download):
    # Playlist: Album - HIVE (Sub Urban)
    download(
        "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    )


class TestExceptions:
    def test_ffmpeg_not_exists(self):
        with pytest.raises(FileNotFoundError):
            MediaDownloader(ffmpeg_path="./unkdown_path/")


class TestSite:
    def test_youtube(self, download):
        # Include subtitles
        download("https://youtu.be/HVmeWkqIYqo")

    def test_ytmusic(self, download):
        download("https://music.youtube.com/watch?v=Kx7B-XvmFtE")

    def test_tiktok(self, download):
        download("https://www.tiktok.com/@livewallpaper77/video/7410777368064806149")

    def test_bandcamp(self, download):
        download("https://gourmetdeluxxx.bandcamp.com/track/nocturnal-hooli")

    def test_soundcloud_playlist(self, download):
        download("https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth")
