"""Media-DL exceptions."""


class MediaError(Exception):
    """Base exception."""


class OutputTemplateError(KeyError):
    """Output template error."""


class DownloadError(ConnectionError):
    """Download error."""


class PostProcessingError(DownloadError):
    """Postprocessing error."""


class ExtractError(ConnectionError):
    """Extraction error."""
