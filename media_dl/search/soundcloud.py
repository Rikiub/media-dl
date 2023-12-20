from itertools import islice

from soundcloud import SoundCloud as SoundCloudClient

from media_dl.search.base import SearchProvider, Result


class Soundcloud(SearchProvider):
    def __init__(self, client_id: str | None = None):
        if client_id:
            self.client = SoundCloudClient(client_id=client_id)
        else:
            self.client = SoundCloudClient()

    def search(self, query: str) -> list[Result]:
        results: list[Result] = []

        for track in islice(self.client.search_tracks(query), 20):
            results.append(
                Result(
                    source=self.name,
                    id=str(track.id),
                    url=track.permalink_url,
                    title=track.title,
                    uploader=track.user.username,
                    duration=track.full_duration,
                    thumbnail=track.artwork_url,
                )
            )
        return results


if __name__ == "__main__":
    from rich import print

    x = Soundcloud()
    result = x.search("Sub Urban")
    print(result)
