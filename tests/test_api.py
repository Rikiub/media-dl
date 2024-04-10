from tempfile import TemporaryDirectory

from media_dl import extract_url, Downloader, Stream

TEMPDIR = TemporaryDirectory()


def test_api_syntax():
    URL = "https://music.youtube.com/watch?v=hkcN1FnjmbU"

    downloader = Downloader("audio", quality=1, output=TEMPDIR.name)
    result = extract_url(URL)

    with TEMPDIR:
        # If is a stream, filter by best quality and download.
        if stream := isinstance(result, Stream) and result.update():
            format = stream.formats.filter(type="audio").get_best_quality()
            path = downloader.download_single(stream, format)

        # Or just download any result.
        else:
            path = downloader.download_multiple(result)

    print(path)
