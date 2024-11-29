from tempfile import TemporaryDirectory

try:
    from rich import print
except ImportError:
    from pprint import pprint

    print = pprint

import media_dl

TEMPDIR = TemporaryDirectory()

URL = "https://www.youtube.com/watch?v=BaW_jenozKc"
PLAYLIST = (
    "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
)


def test_simple():
    stream = media_dl.extract_url(URL)
    path = media_dl.StreamDownloader(
        "audio", quality=1, output=TEMPDIR.name
    ).download_all(stream)

    print(path)


def test_complex():
    with TEMPDIR:
        downloader = media_dl.StreamDownloader("audio", quality=1, output=TEMPDIR.name)

        result = media_dl.extract_url(PLAYLIST)

        match result:
            case media_dl.Stream():
                path = downloader.download(
                    result,
                    on_progress=lambda *args: print(*args),
                )
                print(path)
            case media_dl.Playlist():
                paths = downloader.download_all(result)
                print(paths)


def test_format_filter():
    stream = media_dl.extract_url(URL)

    if isinstance(stream, media_dl.Stream):
        formats = stream.formats

        fmt = formats.filter("video")
        assert all(isinstance(f, media_dl.VideoFormat) for f in fmt)
        print("VIDEOS:")
        print(fmt)

        fmt = formats.filter("audio")
        assert all(isinstance(f, media_dl.AudioFormat) for f in fmt)
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
