import requests

from media_dl.providers.base import SearchProvider, Result


class YouTubePiped(SearchProvider):
    def __init__(self):
        self.session = requests.Session()

    def search(self, query: str) -> list[Result]:
        response = self.session.get(
            "https://pipedapi.kavin.rocks/search",
            params={"q": query, "filter": ["videos"]},
            timeout=15,
        )
        search_results = response.json()["items"]

        results: list[Result] = []

        for item in search_results:
            results.append(
                Result(
                    source=self.name,
                    id=item["url"].split("?v=")[1],
                    title=item["title"],
                    uploader=item["uploaderName"],
                    duration=item["duration"],
                    url="https://piped.video" + item["url"],
                    thumbnail_url=item["thumbnail"],
                )
            )
        return results


if __name__ == "__main__":
    from rich import print

    client = YouTubePiped()
    results = client.search("Sub Urban")
    print(results)
