from argparse import ArgumentParser, Namespace
from pathlib import Path

OPERATIONS = ("textual", "tui")

def check_path(path: str) -> None:
    path = Path(path)
    if path.exists():
        return path
    else:
        raise ValueError(f"{path} not exist")

def parseArguments() -> Namespace:
	"""
	CLI: argparse initizalizer
	"""

	parser = ArgumentParser(
		prog="Media-DL",
		description="media downloader"
	)
	parser.add_argument(
		"operation",
		help="what you want do?",
		choices=OPERATIONS, type=str,
		nargs="?"
	)
	parser.add_argument(
		"-o", "--output",
		help="directory where the playlists will be stored",
		default=Path.cwd(), type=check_path
	)

	return parser.parse_args()