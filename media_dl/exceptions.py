class MediaError(Exception):
    """Base exception."""


class DownloadError(MediaError):
    """Error related to download."""


class ExtractError(MediaError):
    """Error related to info extraction."""
