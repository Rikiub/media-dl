from tempfile import TemporaryDirectory

import media_dl

TEMPDIR = TemporaryDirectory()


def test_api_syntax():
    URL = "https://music.youtube.com/watch?v=hkcN1FnjmbU"

    downloader = media_dl.Downloader("audio", quality=1, output=TEMPDIR.name)
    result = media_dl.extract_url(URL)

    with TEMPDIR:
        # If is a stream, filter by best quality and download.
        if isinstance(result, media_dl.Stream):
            format = result.formats.filter(type="audio").get_best_quality()
            path = downloader.download(result, format, lambda *args: print(*args))

        # Or just download any result.
        else:
            path = downloader.download_all(result)

    print(path)


if __name__ == "__main__":
    test_api_syntax()
