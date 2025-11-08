"""Media-DL API. Handler for URLs extraction, serialization and streams download."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .__init_exports import *  # noqa: F403
else:
    from lazy_imports import LazyModule, load, module_source, as_package

    load(
        LazyModule(
            *as_package(__file__),
            module_source(".__init_exports", __name__),
            name=__name__,
            doc=__doc__,
        )
    )
