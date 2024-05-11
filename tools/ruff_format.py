import subprocess
from pathlib import Path

project_path = Path(__file__).parent.parent


def run():
    subprocess.run(["ruff", "check", "--select", "I", "--fix", str(project_path)])
    subprocess.run(["ruff", "format", str(project_path)])


if __name__ == "__main__":
    run()
