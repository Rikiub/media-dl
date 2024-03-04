from rich import print

from media_dl import YDL, Stream

if __name__ == "__main__":

    url = "https://www.youtube.com/watch?v=BaW_jenozKc"
    url_playlist = "https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth"

    print("Extrayendo")
    ydl = YDL(format="only-audio", output="temp")
    result = ydl.extract_search("Sub urban", "soundcloud")
    print("Extraccion finalizada")

    if isinstance(result, Stream):
        format = result.formats.filter("video")
        print(format[-1].display_quality)
    else:
        pass
