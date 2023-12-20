from abc import ABC, abstractmethod

from media_dl.types import Result


class SearchProvider(ABC):
    """Base class for search engines."""

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def search(self, query: str) -> list[Result]:
        """Get information from a search provider by search term.

        Returns:
            List of `Result`.
        """
        raise NotImplementedError
