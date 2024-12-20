from media_dl.path import CACHE_DIR

DIR = CACHE_DIR / "info"
DIR.mkdir(parents=True, exist_ok=True)


class JsonCache:
    """Stream cache handler"""

    def __init__(self, url: str) -> None:
        self.url = url
        self.path = DIR / f"{self._clear_url(url)}.json"

    def exists(self) -> bool:
        return self.path.is_file()

    def get(self) -> str | None:
        if self.exists():
            return self.path.read_text()

    def save(self, json: str) -> None:
        with self.path.open("w") as f:
            f.write(json)

    def remove(self) -> bool:
        if self.exists():
            self.path.unlink()
            return True
        else:
            return False

    def _clear_url(self, url: str) -> str:
        return url.replace("http://", "").replace("https://", "").replace("/", "_")
