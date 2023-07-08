from arguments import parseArguments, OPERATIONS
import sys

from interface.textual.app import MediaDLApp
from interface.tui import TUI

if __name__ == "__main__":
	args = parseArguments()

	if args.operation == "textual" or not sys.argv[0]:
		MediaDLApp().run()
	elif args.operation == "tui":
		TUI()