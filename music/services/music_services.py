from __future__ import annotations

from music.services.youtube import YoutubeService
from music.services.spotify import SpotifyService
from music.services.media_loader import MediaLoader
from music.services.media_resolver import MediaResolver


class MusicServices:

    def __init__(self):

        self.youtube = YoutubeService()
        self.spotify = SpotifyService()
        self.loader = MediaLoader()
        self.resolver = MediaResolver()