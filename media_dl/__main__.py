from arguments import parseArguments, OPERATIONS

if __name__ == "__main__":
	args = parseArguments()

	if args.operation == "textual":
		from textual_ui.app import YDLApp
		YDLApp().run()