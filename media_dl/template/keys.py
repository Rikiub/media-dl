from pathlib import Path
import json

FILEPATH = Path(Path(__file__).parent, "template.json")


def get_template_keys() -> list[str]:
    with FILEPATH.open() as f:
        return json.load(f)


OUTPUT_TEMPLATES = get_template_keys()
