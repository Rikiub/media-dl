"""Media-DL exceptions."""


class MediaError(Exception):
    """Media-DL base exception."""


class DownloadError(MediaError):
    """Download error."""


class ExtractError(MediaError):
    """Extraction error."""
