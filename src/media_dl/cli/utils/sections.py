from enum import Enum


class HelpPanel(str, Enum):
    file = "File"
    downloader = "Downloader"
    other = "Other"
