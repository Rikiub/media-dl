from tempfile import TemporaryDirectory

import media_dl

TEMPDIR = TemporaryDirectory()

URL = "https://music.youtube.com/watch?v=hkcN1FnjmbU"


def test_api():
    result = media_dl.extract_url(URL)

    with TEMPDIR:
        downloader = media_dl.Downloader("audio", quality=1, output=TEMPDIR.name)

        # If is stream, filter by best quality and download.
        if isinstance(result, media_dl.Stream):
            format = result.formats.filter(type="audio").get_best_quality()
            path = downloader.download(
                result,
                format,
                on_progress=lambda *args: print(*args),
            )

        # Or just download any result.
        else:
            path = downloader.download_all(result)

    print(path)


if __name__ == "__main__":
    test_api()
