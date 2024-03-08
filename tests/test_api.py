from tempfile import TemporaryDirectory

from rich import print

from media_dl import MediaDL

TEMPDIR = TemporaryDirectory()


def test_api_syntax():
    ydl = MediaDL(format="audio", output=TEMPDIR.name)

    print("Extraction")
    result = ydl.extract_search("Sub urban", "soundcloud")
    print("Extraction Done")

    print("Update")
    stream = result[0].update()
    print("Update Done")

    print("Filter")
    format = stream.formats.filter("audio").get_best_quality()
    print("Filter Done")

    with TEMPDIR:
        path = ydl.download(stream, format)
        print(path)


if __name__ == "__main__":
    test_api_syntax()
