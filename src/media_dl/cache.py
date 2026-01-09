import hashlib
import time

from media_dl.path import CACHE_DIR

EXPIRATION = 24 * 60 * 60


def load_info(url: str) -> str | None:
    file = CACHE_DIR / _url_hash(url)

    if file.exists():
        age = time.time() - file.stat().st_mtime
        if age < EXPIRATION:
            return file.read_text()

    return None


def save_info(url: str, content: str):
    file = CACHE_DIR / _url_hash(url)
    file.write_text(content)


def _url_hash(url: str) -> str:
    hash = hashlib.sha256(url.encode()).hexdigest()
    return f"{hash}.json"
