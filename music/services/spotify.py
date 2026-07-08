from __future__ import annotations

from spotify_scraper import AsyncSpotifyClient

from music.models import SpotifyTrack

from urllib.parse import urlparse


class SpotifyService:

    def _create_track(
        self,
        track,
    ) -> SpotifyTrack:

        artists = ", ".join(
            artist.name
            for artist in track.artists
        )

        return SpotifyTrack(
            title=track.name,
            artist=artists,
        )

    async def resolve_track(
        self,
        url: str,
    ) -> SpotifyTrack:

        async with AsyncSpotifyClient() as client:
            track = await client.get_track(url)

        return self._create_track(track)

    async def resolve_album(
        self,
        url: str,
    ) -> list[SpotifyTrack]:

        async with AsyncSpotifyClient() as client:
            album = await client.get_album(url)

        return [
            self._create_track(track)
            for track in album.tracks
        ]

    async def resolve_playlist(
        self,
        url: str,
    ) -> list[SpotifyTrack]:

        async with AsyncSpotifyClient() as client:
            playlist = await client.get_playlist(url)

        tracks: list[SpotifyTrack] = []

        for item in playlist.tracks:

            if item.track is None:
                continue

            tracks.append(
                self._create_track(item.track)
            )

        return tracks
    
    async def resolve(
        self,
        url: str,
    ) -> list[SpotifyTrack]:
        
        parsed = urlparse(url)
        
        parts = parsed.path.strip("/").split("/")
        
        if parts and parts[0].startswith("intl-"):
            parts = parts[1:]
            
        if len(parts) < 2:
            raise ValueError("Enlace de Spotify inválido.")
        
        tipo = parts[0]
        
        if tipo == "track":
            
            return [
                await self.resolve_track(url)
            ]
        
        if tipo == "album":
            
            return await self.resolve_album(url)
        
        if tipo == "playlist":
            
            return await self.resolve_playlist(url)
        
        raise ValueError(
            f"Tipo de Spotify no soportado: {tipo}"
        )