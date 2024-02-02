> yt-dlp helper with nice defaults + fancy output + music metadata.

## Features

- Helper for yt-dlp handled by file extension with nice defaults:
    - Metadata
    - Thumbnails
    - Subtitles
    - Simple API and extra validations
- Music search for:
    - YouTube Music
    - SoundCloud
- Multiple threads for fast downloads.
- Pretty and fancy CLI interface.
- Basic metadata and synced lyrics for music sites.
- Sync playlists

## No supported

- Bulk download of channels (Or anything with multiple Playlists).

## Dependencies

- [yt-dlp](https://pypi.org/project/yt-dlp/): Video and Audio downloader.
- [Typer](https://pypi.org/project/typer/): Fancy CLI interface.
- [Rich](https://pypi.org/project/rich/): Fancy output and progress bars.

## TODO

- [ ] YTMusic and SoundCloud search.
- [ ] Better video quality selector.
- [ ] Sync playlists feature.
- [ ] Refactorize CLI UI components.
- [x] Handler for music-sites metadata + syncedlyrics.
- [x] Good yt-dlp API helper.
