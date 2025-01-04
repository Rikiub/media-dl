"""Media-DL exceptions."""


class MediaError(Exception):
    """Base exception."""


class OutputTemplateError(MediaError, KeyError):
    """Output template error."""


class DownloadError(MediaError, ConnectionError):
    """Download error."""


class PostProcessingError(MediaError):
    """Postprocessing error."""


class ExtractError(MediaError, ConnectionError):
    """Extraction error."""
