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


def test_api():
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

        videos = formats.filter("video")
        print(videos)

        audios = formats.filter("audio")
        print(audios)

        best_quality = formats.get_best_quality()
        print(best_quality)

        by_id = formats.get_by_id("137")
        print(by_id)


if __name__ == "__main__":
    test_api()
