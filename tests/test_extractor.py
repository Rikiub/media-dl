import pytest
from rich import print

from media_dl import Playlist, Search, Stream
from media_dl.exceptions import ExtractError
from media_dl.types import SEARCH_PROVIDER


def extract_url(url: str) -> Stream | Playlist:
    try:
        result = Stream.from_url(url)
    except TypeError:
        result = Playlist.from_url(url)

    print(result)
    return result


def test_exceptions():
    # Invalid URL
    with pytest.raises(ExtractError):
        extract_url("https://unkdown.link.com/")

    # YouTube [Private video]
    with pytest.raises(ExtractError):
        extract_url("https://www.youtube.com/watch?v=yi50KlsCBio")

    # YouTube [Deleted video]
    with pytest.raises(ExtractError):
        extract_url("https://www.youtube.com/watch?v=JUf1zxjR_Qw")


class TestBase:
    def test_stream(self):
        result = extract_url("https://youtube.com/watch?v=Kx7B-XvmFtE")
        assert isinstance(result, Stream)

    def test_playlist(self):
        result = extract_url(
            "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
        )
        assert isinstance(result, Playlist)


class TestSearch:
    QUERY = "Sub Urban - Rabbit Hole"

    def search(self, provider: SEARCH_PROVIDER):
        search = Search.from_query(self.QUERY, provider)
        streams = search.streams

        assert isinstance(streams, list) and len(streams) > 0
        print(streams)

    def test_youtube(self):
        self.search("youtube")

    def test_soundcloud(self):
        self.search("soundcloud")

    def test_ytmusic(self):
        self.search("ytmusic")

    def test_extract_streams(self):
        result = Search.from_query("If Nevermore", "ytmusic")

        for entry in result.streams:
            entry = entry.resolve()
            print(entry)

    def test_extract_playlists(self):
        result = Search.from_query("If Nevermore", "ytmusic")

        for entry in result.playlists:
            entry = entry.resolve()
            print(entry)


class TestSite:
    def test_youtube(self):
        extract_url("https://www.youtube.com/watch?v=lBVhLcfoahw ")

    def test_ytmusic(self):
        extract_url("https://music.youtube.com/watch?v=Kx7B-XvmFtE")

    """
    [facebook] 2868837949958495: Cannot parse data;
    
    def test_facebook(self):
        extract_url(
            "https://www.facebook.com/share/v/wfwaBTuUg2eWpd6m/?mibextid=rS40aB7S9Ucbxw6v"
        )
    """

    def test_tiktok(self):
        extract_url("https://www.tiktok.com/@livewallpaper77/video/7410777368064806149")

    def test_reddit(self):
        extract_url(
            "https://www.reddit.com/r/videos/comments/1ggnre2/i_bought_a_freeze_dryer_so_you_dont_have_to"
        )

    def test_pinterest(self):
        extract_url("https://www.pinterest.com/pin/762304674460692892/")

    def test_soundcloud(self):
        extract_url("https://api.soundcloud.com/tracks/1269676381")
