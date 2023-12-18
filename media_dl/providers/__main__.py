from media_dl.providers import get_provider

from rich import print

provider = get_provider("soundcloud")

print("Searching with:", provider.name)
search_result = provider.search("Sub Urban")
print(search_result)
