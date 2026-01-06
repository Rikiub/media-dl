from tempfile import TemporaryDirectory

from media_dl import AudioFormat, Playlist, Stream, StreamDownloader, VideoFormat

try:
    from rich import print

    pprint = print
except ImportError:
    from pprint import pprint as _pprint

    pprint = _pprint


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

        pprint(path)


def test_advanced():
    with TEMPDIR:
        downloader = StreamDownloader("audio", quality=1, output=TEMPDIR.name)

        try:
            result = Stream.from_url(URL)
            paths = downloader.download(
                result,
                on_progress=lambda *args: pprint(*args),
            )
        except TypeError:
            result = Playlist.from_url(PLAYLIST)
            paths = downloader.download_all(result)

        pprint(paths)


def test_format_filter():
    formats = Stream.from_url(URL).formats

    fmt = formats.filter("video")
    assert all(isinstance(f, VideoFormat) for f in fmt)
    pprint("VIDEOS:")
    pprint(fmt)

    fmt = formats.filter("audio")
    assert all(isinstance(f, AudioFormat) for f in fmt)
    pprint("AUDIOS:")
    pprint(fmt)

    fmt = formats.get_best_quality()
    assert fmt.quality == 1080
    pprint("BEST QUALITY:")
    pprint(fmt)

    ID = "137"
    fmt = formats.get_by_id(ID)
    assert fmt.id == ID
    pprint("BY ID:")
    pprint(fmt)
