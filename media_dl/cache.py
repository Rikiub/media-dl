from pathlib import Path
import shutil
import json

from media_dl.dirs import DIR_TEMP
from media_dl.helper import InfoDict, info_extract_meta


class InfoStore:
    """Info-Dict store to avoid repetitive requests."""

    def __init__(self, tempdir: Path | str) -> None:
        self.tempdir = Path(tempdir) / "info_cache"
        self.tempdir.mkdir(parents=True, exist_ok=True)

    def load(self, extractor: str, id: str) -> InfoDict | None:
        """Load a info-dict. Returns it if exist."""

        file = self._prepare_filename(extractor, id)

        if file.exists():
            return json.loads(file.read_text())
        else:
            return None

    def save(self, info: InfoDict) -> None:
        """Save a info-dict for future use."""

        extractor, id, _ = info_extract_meta(info)
        file = self._prepare_filename(extractor, id)

        if not file.exists():
            file.write_text(json.dumps(info))
        else:
            return None

    def clean(self) -> None:
        """Delete store directory."""

        shutil.rmtree(self.tempdir)

    def _prepare_filename(self, extractor: str, id: str) -> Path:
        name = extractor + " - " + id + ".info.json"
        return Path(self.tempdir, name)


GLOBAL_INFO = InfoStore(DIR_TEMP)
