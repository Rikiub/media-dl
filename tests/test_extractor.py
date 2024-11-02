import pytest
from rich import print

from media_dl.exceptions import ExtractError
from media_dl import api as media_dl
from media_dl.models.playlist import Playlist
from media_dl.models.stream import LazyStreams, Stream
from media_dl.types import SEARCH_PROVIDER


def extract_url(url: str):
    result = media_dl.extract_url(url)
    print(result)
    return result


def test_invalid_url():
    with pytest.raises(ExtractError):
        extract_url("https://unkdown.link.com/")


def test_others_exceptions():
    # YouTube [Private video]
    with pytest.raises(ExtractError):
        extract_url("https://www.youtube.com/watch?v=yi50KlsCBio")

    # YouTube [Deleted video]
    with pytest.raises(ExtractError):
        extract_url("https://www.youtube.com/watch?v=JUf1zxjR_Qw")


class TestBase:
    def test_stream(self):
        result = extract_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        assert isinstance(result, Stream)

    def test_playlist(self):
        result = extract_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(result, Playlist)


class TestSearch:
    QUERY = "Sub Urban - Rabbit Hole"

    def search(self, provider: SEARCH_PROVIDER):
        streams = media_dl.extract_search(self.QUERY, provider)
        assert isinstance(streams, LazyStreams)
        print(streams)

    def test_youtube(self):
        self.search("youtube")

    def test_ytmusic(self):
        self.search("ytmusic")

    def test_soundcloud(self):
        self.search("soundcloud")


class TestSite:
    def test_ytmusic(self):
        extract_url("https://music.youtube.com/watch?v=Kx7B-XvmFtE")

    def test_tiktok(self):
        extract_url("https://www.tiktok.com/@livewallpaper77/video/7410777368064806149")

    def test_reddit(self):
        extract_url(
            "https://www.reddit.com/r/videos/comments/1ggnre2/i_bought_a_freeze_dryer_so_you_dont_have_to"
        )

    def test_pinterest(self):
        extract_url("https://pin.it/61ZG0pA41")
