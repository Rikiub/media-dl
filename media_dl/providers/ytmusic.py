from ytmusicapi import YTMusic as YT

from media_dl.providers.base import URL_BASE, YDLGeneric, Result


class YTMusic(YDLGeneric):
    PROVIDER_TYPE = "only_audio"
    URL_BASE = ["https://music.youtube/"]

    def __init__(self, **kwars):
        super().__init__(**kwars)
        self.client = YT()

    def search(self, query: str) -> list[Result]:
        info = self.client.search(query, filter="songs")
        results: list[Result] = []

        for track in info:
            if not track or not track.get("videoId") or not any(track["artists"]):
                continue

            results.append(
                Result(
                    type=self.PROVIDER_TYPE,
                    source=self.name,
                    id=track["videoId"],
                    title=track["title"],
                    uploader=track["artists"][0]["name"],
                    duration=track["duration_seconds"],
                    url=(
                        f'https://{"music" if track["resultType"] == "song" else "www"}'
                        f'.youtube.com/watch?v={track["videoId"]}'
                    ),
                    thumbnail_url=track["thumbnails"][-1]["url"],
                )
            )
        return results


if __name__ == "__main__":
    from rich import print

    x = YTMusic()
    x = x.search("Sub Urban")
    print(x)
