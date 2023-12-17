> Helper for yt-dlp with nice defaults + fancy output + music metadata.

## Features

- Helper for **yt-dlp** handled by file extension.
	- Embed metadata, lyrics and thumbnail if extension is audio 🎵.
	- Embed metadata, subtitles and thumbnail if extension is video 📹.
- Music search, metadata and lyrics search (**Spotify API** + **syncedlyrics**).

## Dependencies

- **Base**
	- [yt-dlp](https://pypi.org/project/yt-dlp/): Video and Audio downloader.
	- [Typer](https://pypi.org/project/typer/): Fancy CLI interface.
	- [Rich](https://pypi.org/project/rich/): Fancy output and progress bars.
- **Music**
	- [syncedlyrics](https://pypi.org/project/syncedlyrics/): Synced lyrics support.
	- [music-tag](https://pypi.org/project/music-tag/): Audio metadata parser (Wrapper for Mutagen).
	- [spotipy](https://pypi.org/project/spotipy/): Music metadata scrapper.

## ROADMAP

- [ ] Sync playlists feature.
- [ ] Video search providers.
	- [ ] YouTube
	- [ ] Piped
- [ ] Music search providers.
	- [ ] YouTube Music
	- [ ] Soundlocud
	- [ ] Bandcamp

---

- [x] Good yt-dlp API helper.
- [x] Spotify metadata provider (Spotipy).
- [x] Music lyrics provider (Syncedlyrics).
- [x] View/Parse music metadata of file from search (Spotify).

## TODO

- [ ] Refactorize CLI UI components.
