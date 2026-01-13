from dataclasses import dataclass

from media_dl.types import LOGGING_LEVELS


@dataclass(slots=True)
class _Config:
    verbose: bool = False
    quiet: bool = False

    @property
    def log_level(self) -> LOGGING_LEVELS:
        if self.quiet:
            return "CRITICAL"
        elif self.verbose:
            return "DEBUG"
        else:
            return "INFO"


CONFIG = _Config()
