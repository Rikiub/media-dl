from itertools import islice
import mimetypes

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
            formats: list[dict] = []

            for stream in track.media.transcodings:
                mime_type = stream.format.mime_type.split(";")[0]
                mime_type = mimetypes.guess_extension(mime_type)
                mime_type = mime_type[1:] if mime_type is not None else "none"

                formats.append(
                    {
                        "url": stream.url + "?client_id=" + self.client.client_id,
                        "ext": mime_type,
                        "protocol": stream.format.protocol,
                    }
                )

            results.append(
                Result(
                    source=self.name,
                    id=str(track.id),
                    url=track.permalink_url,
                    title=track.title,
                    uploader=track.user.username,
                    duration=track.full_duration,
                    thumbnail=track.artwork_url,
                    _formats=formats,
                )
            )
        return results


if __name__ == "__main__":
    from rich import print

    x = Soundcloud()
    result = x.search("Sub Urban")
    print(result)
