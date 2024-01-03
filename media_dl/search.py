from typing import Literal
import requests
from requests.exceptions import HTTPError

from media_dl.types import Result

PIPEDAPI_INSTANCE = "pipedapi.kavin.rocks"


class YoutubeSearch:
    def __init__(self):
        self.session = requests.Session()

    def search(
        self, query: str, provider: Literal["youtube", "ytmusic"]
    ) -> list[Result]:
        if provider == "youtube":
            scope = ["videos"]
        elif provider == "ytmusic":
            scope = ["music_songs"]
        else:
            raise ValueError(f'{provider} is invalid. Must be "youtube" or "ytmusic".')

        response = self.session.get(
            "https://" + PIPEDAPI_INSTANCE + "/search",
            params={"q": query, "filter": scope},
            timeout=10,
        )

        # Check if instance is out of service.
        if response.status_code != 200:
            raise HTTPError(PIPEDAPI_INSTANCE + " returned error", response.status_code)

        search_results = response.json()

        results: list[Result] = []
        for item in search_results["items"]:
            url: str = "https://piped.video" + item["url"]

            results.append(
                Result(
                    url=url,
                    thumbnail=item["thumbnail"],
                    extractor="Youtube",
                    id=item["url"].split("?v=")[1],
                    title=item["title"],
                    uploader=item["uploaderName"],
                    duration=item["duration"],
                )
            )
        return results


if __name__ == "__main__":
    from rich import print

    client = YoutubeSearch()
    results = client.search("Sub Urban", "ytmusic")
    print(results)
