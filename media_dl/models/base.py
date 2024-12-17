from typing import Annotated

from pydantic import AliasChoices, BaseModel, Field


class ExtractID(BaseModel):
    """Base identifier for media objects."""

    extractor: Annotated[
        str,
        Field(
            alias="extractor_key",
            validation_alias=AliasChoices("extractor_key", "ie_key"),
        ),
    ]
    url: Annotated[str, Field(validation_alias=AliasChoices("original_url", "url"))]
    id: str
