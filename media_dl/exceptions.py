"""Media-DL exceptions."""


class MediaError(Exception):
    """Base exception."""


class DownloadError(MediaError):
    """Download error."""


class ExtractError(MediaError):
    """Info extraction error."""
