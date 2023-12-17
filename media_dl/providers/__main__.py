from media_dl.providers import get_provider

from rich import print

provider = get_provider("soundcloud", format=("m4a", 9))

print("Searching with:", provider.name)
search_result = provider.search("Sub Urban")
print(search_result)

print("Downloading")
filename = provider.download(search_result[0].url)
print(filename.absolute())
