"""Media-DL API. Handler for URLs extraction, serialization and streams download."""

from media_dl.download.downloader import Downloader
from media_dl.extractor.extr import extract_url, extract_search
from media_dl.models import Playlist, Stream, Format, ExtractResult
from media_dl.exceptions import DownloadError, ExtractError, MediaError
