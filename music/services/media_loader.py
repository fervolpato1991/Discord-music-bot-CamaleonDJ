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
        concurrency: int = 5,
    ) -> list[Media]:
        
        sem = asyncio.Semaphore(concurrency)
        
        async def worker(track: SpotifyTrack):
            
            async with sem:
                
                query = f"{track.title} {track.artist}"
                
                try:

                    media = await self.youtube.search_best(
                        track.title,
                        track.artist,
                    )
                    
                    return media
                
                except Exception as e:
                    
                    logger.warning(
                        f"No se encontró en YouTube: "
                        f"{track.artist} - {track.title} | "
                        f"Motivo: {e}"
                    )
                    return None
                
        results = await asyncio.gather(
            *(worker(track) for track in tracks)
        )
        
        found = []
        failed = []
        
        for track, media in zip(tracks, results):
            
            if media is None:
                failed.append(track)
            else:
                found.append(media)
                
        logger.info(
            f"Spotify: {len(tracks)} canciones | "
            f"Encontradas: {len(found)} | "
            f"Fallidas: {len(failed)}"
        )
        
        if failed:
            
            logger.warning(
                "Canciones no encontradas:"
            )
            
            for track in failed:
                
                logger.warning(
                    f" - {track.artist} - {track.title}"
                )
            
        return found
    
    async def load_spotify_batch(
            self,
            tracks: list[SpotifyTrack],
            start: int,
            size: int = 10,
        ) -> list[Media]:
        
        batch = tracks[start:start + size]
        
        return await self.load_spotify_tracks(batch)