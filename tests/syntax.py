from media_dl import MediaDL

from rich import print
from rich.traceback import install

install()

media = MediaDL()

stream = media.extract_url("https://music.youtube.com/watch?v=hkcN1FnjmbU")
print(stream)
print(stream._extra_info)

"""
format = stream.formats.filter(type="audio").get_best_quality()  # type: ignore

print("Downloading")
path = media.download_single(stream, format)
print(path)
"""
