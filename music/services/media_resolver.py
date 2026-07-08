from __future__ import annotations

from urllib.parse import urlparse

from music.services.spotify import SpotifyService
from music.services.youtube import YoutubeService


class MediaResolver:

    def __init__(self):

        self.spotify = SpotifyService()
        self.youtube = YoutubeService()

    async def resolve(self, search: str):

        search = search.strip("<>").strip()

        if "spotify.com" in search:
            return "spotify", await self._resolve_spotify(search)

        if "youtube.com" in search or "youtu.be" in search:

            if "list=" in search:
                return "youtube_playlist", await self.youtube.resolve_playlist(search)

            return "youtube_video", await self.youtube.resolve_url(search)

        result = await self.youtube.search_first(search)

        media = await self.youtube.resolve_url(
            result.webpage_url
        )

        return "youtube_search", media

    async def _resolve_spotify(self, url: str):

        parsed = urlparse(url)

        parts = parsed.path.strip("/").split("/")

        if parts and parts[0].startswith("intl-"):
            parts = parts[1:]

        if len(parts) < 2:
            raise ValueError("Enlace Spotify inválido")

        tipo = parts[0]

        if tipo == "track":
            return [await self.spotify.resolve_track(url)]

        if tipo == "album":
            return await self.spotify.resolve_album(url)

        if tipo == "playlist":
            return await self.spotify.resolve_playlist(url)

        raise ValueError("Tipo Spotify no soportado")