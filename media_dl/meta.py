from typing import cast, Literal, get_args
from abc import ABC, abstractmethod
from dataclasses import dataclass
from contextlib import suppress
from pathlib import Path
from io import BytesIO
from enum import Enum
import requests

import music_tag
import syncedlyrics
import musicbrainzngs
from mutagen import _file
from spotipy import Spotify, SpotifyClientCredentials

from media_dl.types import Track
from media_dl.config import APPNAME, SPOTIPY_CREDENTIALS


class BaseMeta(ABC):
    @abstractmethod
    def get_song_metadata(self, query: str, limit: int = 5) -> list[Track] | None:
        raise NotImplementedError


class SpotifyMetadata(BaseMeta):
    def __init__(self, spotipy_credentials: SpotifyClientCredentials):
        self.spotify = Spotify(client_credentials_manager=spotipy_credentials)

    def get_song_metadata(self, query: str, limit: int = 5) -> list[Track] | None:
        songs = []

        if data := self.spotify.search(query, limit=limit):
            data = data["tracks"]["items"]

            for data in data:
                if artist := self.spotify.artist(data["artists"][0]["uri"]):
                    genres = artist["genres"]
                else:
                    genres = None

                songs.append(
                    Track(
                        title=data["name"],
                        album_name=data["album"]["name"],
                        artists=[artist["name"] for artist in data["artists"]],
                        album_artist=data["album"]["artists"][0]["name"],
                        track_number=data["track_number"],
                        tracks_count=data["album"]["total_tracks"],
                        disc_number=data["disc_number"],
                        disc_count=0,
                        year=int(data["album"]["release_date"][0:4]),
                        genres=genres,
                        isrc=data["external_ids"]["isrc"],
                        cover_url=data["album"]["images"][0]["url"],
                    )
                )
            return songs
        else:
            return None


class MusicBrainzMetadata(BaseMeta):
    def get_song_metadata(self, query: str, limit: int = 5) -> list[Track] | None:
        musicbrainzngs.set_useragent(APPNAME, "0.01", "http://example.com")
        mbid = musicbrainzngs.search_recordings(query, limit=limit)

        songs = []
        if "recording-list" in mbid:
            mbid = mbid["recording-list"]

            for song in mbid:
                song = song[0]["id"]

                record = musicbrainzngs.get_recording_by_id(
                    mbid, includes=["artists", "releases"]
                )["recording"]

                song = record["release-list"][0]["id"]
                release = musicbrainzngs.get_release_by_id(
                    mbid, includes=["recordings"]
                )["release"]
                image = musicbrainzngs.get_image_list(mbid)["images"][0]

                release_count = 0
                release_position = 0

                for recording in release["medium-list"][0]["track-list"]:
                    if recording["recording"]["title"] == record["title"]:
                        release_position = int(recording["position"])
                        release_count = int(release["medium-list"][0]["track-count"])

                songs.append(
                    Track(
                        title=record["title"],
                        album_name=release["title"],
                        artists=[
                            artist["artist"]["name"]
                            for artist in record["artist-credit"]
                        ],
                        album_artist=record["artist-credit"][0]["artist"]["name"],
                        track_number=release_position,
                        tracks_count=release_count,
                        disc_number=0,
                        disc_count=0,
                        year=release["date"][0:4],
                        isrc=None,
                        cover_url=image["image"],
                    )
                )
            return songs
        else:
            return None


class Providers(Enum):
    spotify = SpotifyMetadata(SPOTIPY_CREDENTIALS)
    musicbrainz = MusicBrainzMetadata()


PROVIDER = Literal["spotify", "musicbrainz"]


def _sort_instances(selection: list[PROVIDER]) -> list[BaseMeta]:
    sort = []
    args = get_args(PROVIDER)

    for select in selection:
        if select in args:
            sort.append(Providers[select].value)
        else:
            raise ValueError(
                f"{select} not is a valid metadata provider. Must be:", args
            )
    return sort


def search_lyrics(query: str) -> str | None:
    return syncedlyrics.search(query, allow_plain_format=True)


def song_to_file(file: Path, song: Track) -> None:
    f = music_tag.load_file(file)
    f = cast(_file.FileType, f)

    f["tracktitle"] = song.title
    f["album"] = song.album_name
    f["artist"] = song.artists
    f["albumartist"] = song.album_artist
    f["tracknumber"] = song.track_number
    f["totaltracks"] = song.tracks_count
    f["discnumber"] = song.disc_number
    f["totaldiscs"] = song.disc_count
    f["year"] = song.year
    f["genre"] = song.genres
    f["isrc"] = song.isrc
    f["lyrics"] = song.lyrics

    if url := song.cover_url:
        image = requests.get(url).content
        with BytesIO(image) as img:
            f["artwork"] = img.read()

    f.save()
    return


def file_to_song(file: Path) -> Track:
    f = music_tag.load_file(file)
    f = cast(_file.FileType, f)

    return Track(
        title=f["title"].value,
        album_name=f["album"].value,
        artists=f["artist"].value,
        album_artist=f["albumartist"].value,
        track_number=f["tracknumber"].value,
        tracks_count=f["totaltracks"].value,
        disc_number=f["discnumber"].value,
        disc_count=f["totaldiscs"].value,
        year=f["year"].value,
        genres=f["genre"].value,
        isrc=f["isrc"].value,
        lyrics=f["lyrics"].value,
    )


def get_song_list(
    query: str, providers: list[PROVIDER], limit: int = 5
) -> list[Track] | None:
    song_list: list[Track] = []
    error = False

    with suppress(Exception):
        try:
            for item in _sort_instances(providers):
                songs = item.get_song_metadata(query, limit=limit)
                if songs:
                    song_list = songs
                    break

            if song_list:
                for song in song_list:
                    song.lyrics = search_lyrics(f"{song.artists[0]} - {song.title}")
                return song_list
            else:
                return None
        except:
            error = True

    if error:
        raise ConnectionError()


def search_and_embed(query: str, file: Path) -> None:
    if song := get_song_list(query, providers=["spotify", "musicbrainz"], limit=1):
        song_to_file(file, song[0])
    else:
        raise ConnectionError()
