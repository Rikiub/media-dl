from ytmusicapi import YTMusic as YTMusicClient

from media_dl.search.base import SearchProvider, Result


class YTMusic(SearchProvider):
    def __init__(self):
        self.client = YTMusicClient()

    def search(self, query: str) -> list[Result]:
        results: list[Result] = []

        for track in self.client.search(query, filter="songs"):
            if not track.get("videoId") or not any(track["artists"]):
                continue

            results.append(
                Result(
                    extractor=self.name,
                    id=track["videoId"],
                    title=track["title"],
                    uploader=track["artists"][0]["name"],
                    duration=track["duration_seconds"],
                    download=(
                        f'https://{"music" if track["resultType"] == "song" else "www"}'
                        f'.youtube.com/watch?v={track["videoId"]}'
                    ),
                    thumbnail=track["thumbnails"][-1]["url"],
                )
            )
        return results


if __name__ == "__main__":
    from rich import print

    query = "Sub Urban"

    x = YTMusic()
    x = x.search(query)
    print(x)
