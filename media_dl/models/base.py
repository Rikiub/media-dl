from typing import Annotated, Generic, TypeVar, overload

from pydantic import AliasChoices, BaseModel, Field, RootModel
from typing_extensions import Self

T = TypeVar("T")


class ExtractID(BaseModel):
    """Base identifier for media objects."""

    extractor: str = Field(
        alias="extractor_key", validation_alias=AliasChoices("extractor_key", "ie_key")
    )
    url: Annotated[str, Field(validation_alias=AliasChoices("original_url", "url"))]
    id: str


class GenericList(RootModel[list[T]], Generic[T]):
    def __contains__(self, value: object) -> bool:
        return value in self.root

    def __iter__(self):  # type: ignore
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __bool__(self) -> bool:
        return bool(self.root)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    def __getitem__(self, index):
        match index:
            case slice():
                return self.__class__(self.root[index])
            case int():
                return self.root[index]
            case _:
                raise TypeError(index)
