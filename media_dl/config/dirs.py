from platformdirs import PlatformDirs

APPNAME = "media-dl"

dirs = PlatformDirs(APPNAME, ensure_exists=True)
DIR_DOWNLOAD = dirs.user_downloads_path / APPNAME
DIR_TEMP = dirs.site_cache_path
