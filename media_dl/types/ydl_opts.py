import logging

from yt_dlp.postprocessor.metadataparser import MetadataParserPP

from media_dl.config.dirs import DIR_TEMP

_supress_logger = logging.getLogger("YoutubeDL")
_supress_logger.disabled = True


BASE_OPTS = {
    "ignoreerrors": False,
    "no_warnings": True,
    "noprogress": True,
    "quiet": True,
    "logger": _supress_logger,
}
EXTRACT_OPTS = {"skip_download": True, "extract_flat": "in_playlist"}
DOWNLOAD_OPTS = {
    "paths": {
        "home": "",
        "temp": str(DIR_TEMP),
    },
    "outtmpl": {
        "default": "%(uploader)s - %(title)s.%(ext)s",
    },
    "overwrites": False,
    "postprocessors": [
        {
            "key": "FFmpegVideoRemuxer",
            "preferedformat": "opus>ogg/aac>m4a/alac>m4a/mov>mp4/webm>mkv",
        },
        {
            "key": "MetadataParser",
            "when": "pre_process",
            "actions": [
                (
                    MetadataParserPP.interpretter,
                    "%(track,title)s",
                    "%(title)s",
                ),
                (
                    MetadataParserPP.interpretter,
                    "%(channel,uploader,creator,artist|null)s",
                    "%(uploader)s",
                ),
                (
                    MetadataParserPP.interpretter,
                    "%(album_artist,uploader)s",
                    "%(album_artist)s",
                ),
                (
                    MetadataParserPP.interpretter,
                    "%(album,title)s",
                    "%(meta_album)s",
                ),
                (
                    MetadataParserPP.interpretter,
                    "%(release_year,release_date>%Y,upload_date>%Y)s",
                    "%(meta_date)s",
                ),
            ],
        },
    ],
}
