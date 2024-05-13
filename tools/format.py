import subprocess
from pathlib import Path

project_dir = Path(__file__).parent.parent
cache_dir = project_dir / ".ruff_cache"

cache_args = ["--cache-dir", str(cache_dir)]


def run():
    subprocess.run(
        ["ruff", "check", "--select", "I", "--fix", *cache_args, str(project_dir)]
    )
    subprocess.run(["ruff", "format", *cache_args, str(project_dir)])


if __name__ == "__main__":
    run()
