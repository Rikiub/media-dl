> Helper for yt-dlp with nice defaults + fancy output + music metadata.

## Overview

### Features

- Helper for **yt-dlp** handled by file extension.
	- Embed metadata, lyrics and thumbnail if extension is audio 🎵.
	- Embed metadata, subtitles and thumbnail if extension is video 📹.
- Music, metadata and lyrics search (**Spotify API** + **syncedlyrics**).

### Dependencies

- **Base**
	- [yt-dlp](https://pypi.org/project/yt-dlp/): Video and audio downloader.
	- [Typer](https://pypi.org/project/typer/): CLI interface.
	- [Rich](https://pypi.org/project/rich/): Fancy output and progress bars.
- **Music**
	- [syncedlyrics](https://pypi.org/project/syncedlyrics/): Synced lyrics support.
	- [music-tag](https://pypi.org/project/music-tag/): Audio files metadata parser (Wrapper for Mutagen).
	- **Metadata Sources**
		- [spotipy](https://pypi.org/project/spotipy/)
		- [musicbrainzngs](https://pypi.org/project/musicbrainzngs/)

## TODO

- **High Priority**
	- [x] Fix progress bar and show downloaded bytes.
- **Music**
	- [ ] Music download by search with selector.
	- [x] Embed metadata to file from search.
	- [x] Music metadata extractors.
		- [x] Spotify
		- [x] MusicBrainz
	- [x] Music lyrics extractor.

## Interface

- **download**: URLs
	- **output**: Path to save. Default: ==cwd==.
	- **extension**: File extension to detect. Default: ==mp4==.
	- **quality**: Quality of file by range of 0 to 9. Default: ==5==.
	- **threads**: Number of threads to use when download. Default: ==3==.
- **search**: Text
	- **source**: Source to search. Default: ==Spotify==.
		- Spotify
		- SoundCloud
- **meta**: File