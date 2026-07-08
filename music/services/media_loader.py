from __future__ import annotations

import asyncio
import logging

from music.models import Media, SpotifyTrack
from music.services.youtube import YoutubeService

logger = logging.getLogger(__name__)


class MediaLoader:

    def __init__(self):

        self.youtube = YoutubeService()

    async def load_spotify_tracks(
        self,
        tracks: list[SpotifyTrack],
        concurrency: int = 20,
    ) -> list[Media]:

        sem = asyncio.Semaphore(concurrency)

        async def worker(track: SpotifyTrack):

            async with sem:

                query = f"{track.title} {track.artist}"

                try:

                    return await self.youtube.search_first(query)

                except Exception as e:

                    logger.warning(
                        f"No se encontró en YouTube: "
                        f"{track.title} - {track.artist} ({e})"
                    )

                    return None

        results = await asyncio.gather(
            *[worker(track) for track in tracks]
        )

        return [
            media
            for media in results
            if media is not None
        ]