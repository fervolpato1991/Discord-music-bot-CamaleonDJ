from __future__ import annotations

from spotify_scraper import AsyncSpotifyClient

from music.models import SpotifyTrack


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