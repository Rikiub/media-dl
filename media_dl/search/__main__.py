from media_dl.search import SearchProvider

from rich import print

provider = SearchProvider.soundcloud.value()

print("Searching with:", provider.name)
search_result = provider.search("Sub Urban")
print(search_result)
