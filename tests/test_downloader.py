from tempfile import TemporaryDirectory

import pytest

from media_dl import Playlist, Media, MediaDownloader

TEMPDIR = TemporaryDirectory()


downloader = MediaDownloader(
    quality=1,
    output=TEMPDIR.name,
    use_cache=True,
)


def download(url):
    try:
        result = Media.from_url(url)
    except TypeError:
        result = Playlist.from_url(url)

    paths = downloader.download_all(result)

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)


def test_ffmpeg_not_exists():
    with pytest.raises(FileNotFoundError):
        MediaDownloader(ffmpeg_path="./unkdown_path/")


def test_media():
    download("https://youtube.com/watch?v=Kx7B-XvmFtE")


def test_playlist():
    # Playlist: Album - HIVE (Sub Urban)
    download(
        "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    )


def test_subtitles():
    download("https://youtu.be/HVmeWkqIYqo")


class TestSite:
    def test_ytmusic(self):
        download("https://music.youtube.com/watch?v=Kx7B-XvmFtE")

    def test_tiktok(self):
        download("https://www.tiktok.com/@livewallpaper77/video/7410777368064806149")

    def test_bandcamp(self):
        download("https://gourmetdeluxxx.bandcamp.com/track/nocturnal-hooli")

    def test_soundcloud_playlist(self):
        download("https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth")
