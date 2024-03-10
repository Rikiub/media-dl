from yt_dlp import YoutubeDL
from copy import copy

URL = "https://music.youtube.com/watch?v=zgjcNd2EqvQ"
PARAMS = {
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "nopostoverwrites": True,
            "preferredcodec": None,
            "preferredquality": None,
        }
    ],
}

ydl = YoutubeDL(PARAMS)
info = ydl.extract_info(URL, download=False)

ydl2 = copy(ydl)
ydl2.params |= {"format": "251"}

info = ydl2.process_ie_result(info, download=True)
