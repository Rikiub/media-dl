"""Media-DL API. Handler for URLs extraction, serialization and medias download."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .__init_exports import *  # noqa: F403
else:
    from lazy_imports import LazyModule, as_package, load, module_source
    from loguru import logger

    logger.disable("media_dl")

    load(
        LazyModule(
            *as_package(__file__),
            module_source(".__init_exports", __name__),
            name=__name__,
            doc=__doc__,
        )
    )
