"""Media-DL exceptions."""


class MediaError(Exception):
    """Base exception."""


class DownloadError(MediaError):
    """Download error."""


class PostProcessingError(DownloadError):
    """Postprocessing error."""


class ExtractError(ConnectionError, MediaError):
    """Extraction error."""
