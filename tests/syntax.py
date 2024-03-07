from media_dl import YDL
from rich import print

ydl = YDL(format="audio", output="temp")

result = ydl.extract_search("Sub urban", "soundcloud")

print("filtrando")
stream = result[0].update()
format = stream.formats.filter("audio").get_best_quality()

print(result)

ydl.download(stream, None)
