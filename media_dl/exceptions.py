class MediaError(Exception):
    """Base exception."""


class DownloadError(MediaError):
    pass


class ExtractError(MediaError):
    pass
