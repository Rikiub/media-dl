from tempfile import TemporaryDirectory

import media_dl
from media_dl.models import Stream

TEMPDIR = TemporaryDirectory()


def test_api_syntax():
    URL = "https://music.youtube.com/watch?v=hkcN1FnjmbU"

    downloader = media_dl.Downloader("audio", quality=1, output=TEMPDIR.name)
    result = media_dl.extract_url(URL)

    with TEMPDIR:
        if stream := isinstance(result, Stream) and result.update():
            format = stream.formats.filter(type="audio").get_best_quality()
            path = downloader.download_single(stream, format)
        else:
            path = downloader.download_multiple(result)

        print(path)
