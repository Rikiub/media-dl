from itertools import islice

from soundcloud import SoundCloud as SC

from media_dl.types import Result
from media_dl.providers.base import YDLGeneric


class Soundcloud(YDLGeneric):
    PROVIDER_TYPE = "only_audio"
    URL_BASE = ["https://soundcloud.com/"]

    def __init__(self, client_id: str | None = None, **kwargs):
        super().__init__(**kwargs)

        if client_id:
            self.client = SC(client_id=client_id)
        else:
            self.client = SC()

    def extract_url(self, url: str) -> list[Result]:
        if url.startswith("https://soundcloud.com/"):
            return []
        else:
            return super().extract_url(url)

    def search(self, query: str) -> list[Result]:
        results: list[Result] = []

        for track in islice(self.client.search_tracks(query), 20):
            results.append(
                Result(
                    type=self.PROVIDER_TYPE,
                    source=self.name,
                    id=str(track.id),
                    url=track.permalink_url,
                    title=track.title,
                    uploader=track.user.username,
                    duration=track.full_duration,
                    thumbnail_url=track.artwork_url,
                )
            )
        return results


if __name__ == "__main__":
    from yt_dlp import YoutubeDL
    from rich import print

    print("Searching.")
    x = Soundcloud()
    result = x.search("Sub Urban")
    print(result)

    print("Downloading.")
    with YoutubeDL() as ydl:
        info = ydl.extract_info(result[0].url, download=False)

    print("Finished")
