from tempfile import TemporaryDirectory

from media_dl import Playlist, Stream, StreamDownloader, AudioFormat, VideoFormat

try:
    from rich import print
except ImportError:
    from pprint import pprint

    print = pprint


TEMPDIR = TemporaryDirectory()

URL = "https://youtube.com/watch?v=Kx7B-XvmFtE"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


def test_simple():
    with TEMPDIR:
        stream = Stream.from_url(URL)
        path = StreamDownloader("audio", quality=1, output=TEMPDIR.name).download_all(
            stream
        )

        print(path)


def test_advanced():
    with TEMPDIR:
        downloader = StreamDownloader("audio", quality=1, output=TEMPDIR.name)

        try:
            result = Stream.from_url(URL)
            paths = downloader.download(
                result,
                on_progress=lambda *args: print(*args),
            )
        except TypeError:
            result = Playlist.from_url(PLAYLIST)
            paths = downloader.download_all(result)

        print(paths)


def test_format_filter():
    formats = Stream.from_url(URL).formats

    fmt = formats.filter("video")
    assert all(isinstance(f, VideoFormat) for f in fmt)
    print("VIDEOS:")
    print(fmt)

    fmt = formats.filter("audio")
    assert all(isinstance(f, AudioFormat) for f in fmt)
    print("AUDIOS:")
    print(fmt)

    fmt = formats.get_best_quality()
    assert fmt.quality == 1080
    print("BEST QUALITY:")
    print(fmt)

    ID = "137"
    fmt = formats.get_by_id(ID)
    assert fmt.id == ID
    print("BY ID:")
    print(fmt)
