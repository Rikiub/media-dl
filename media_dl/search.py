from typing import Literal
import requests

from media_dl.types import Result, Url


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
            "https://pipedapi.kavin.rocks/search",
            params={"q": query, "filter": scope},
            timeout=10,
        )
        search_results = response.json()["items"]

        results: list[Result] = []
        for item in search_results:
            url: str = "https://youtube.com" + item["url"]

            results.append(
                Result(
                    url=Url(
                        original=url,
                        download=url,
                        thumbnail=item["thumbnail"],
                    ),
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
    results = client.search("Sub Urban", "youtube")
    print(results)
