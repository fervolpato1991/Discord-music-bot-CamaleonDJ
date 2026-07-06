from __future__ import annotations

import asyncio

import yt_dlp

from music.exceptions import SearchError, StreamError
from music.models import Media, SearchResult
from music.settings import YTDLP_OPTIONS


class YoutubeService:
    """
    Servicio encargado de toda la interacción con YouTube mediante yt-dlp.
    """

    def __init__(self) -> None:
        self._ydl = yt_dlp.YoutubeDL(YTDLP_OPTIONS)

    # ==========================================================
    # MÉTODOS PÚBLICOS
    # ==========================================================

    async def search(self, query: str) -> list[SearchResult]:

        data = await self._extract_info(f"ytsearch:{query}")

        entries = data.get("entries", [])

        if not entries:
            raise SearchError(f"No se encontraron resultados para: {query}")

        return self._parse_search_results(entries)

    async def search_first(self, query: str) -> SearchResult:

        results = await self.search(query)

        return results[0]

    async def resolve_url(self, url: str) -> Media:

        data = await self._extract_info(url)

        return self._create_media(data)
    
    async def resolve_playlist(self, url: str) -> list[Media]:
    
        data = await self._extract_info(url)

        entries = data.get("entries", [])

        if not entries:
            raise SearchError(
                "La playlist no contiene canciones."
            )

        media_list = []

        for entry in entries:

            if not entry:
                continue

            media_list.append(
                self._create_media(entry)
            )

        return media_list

    async def resolve_stream(self, media: Media) -> Media:
        """
        Obtiene la URL real del stream de audio.

        Siempre se ejecuta justo antes de reproducir para evitar
        utilizar URLs expiradas.
        """

        try:

            data = await asyncio.to_thread(
                self._ydl.extract_info,
                media.webpage_url,
                download=False
            )

        except yt_dlp.utils.DownloadError as exc:
            raise StreamError(str(exc)) from exc

        except Exception as exc:
            raise StreamError(str(exc)) from exc

        stream_url = data.get("url")

        if not stream_url:
            raise StreamError(
                "No fue posible obtener la URL del stream."
            )

        return Media(
            title=media.title,
            webpage_url=media.webpage_url,
            stream_url=stream_url,
            duration=media.duration,
            thumbnail=media.thumbnail,
            extractor=media.extractor,
            video_id=media.video_id,
        )

    # ==========================================================
    # MÉTODOS PRIVADOS
    # ==========================================================

    async def _extract_info(self, query: str) -> dict:

        try:

            return await asyncio.to_thread(
                self._ydl.extract_info,
                query,
                download=False
            )

        except yt_dlp.utils.DownloadError as exc:
            raise SearchError(str(exc)) from exc

        except Exception as exc:
            raise SearchError(str(exc)) from exc

    def _parse_search_results(
        self,
        entries: list[dict]
    ) -> list[SearchResult]:

        return [
            self._create_search_result(entry)
            for entry in entries
            if entry
        ]

    def _create_search_result(
        self,
        entry: dict
    ) -> SearchResult:

        webpage_url = (
            entry.get("webpage_url")
            or entry.get("url")
            or (
                f"https://www.youtube.com/watch?v={entry['id']}"
                if entry.get("id")
                else ""
            )
        )

        return SearchResult(
            title=entry.get("title", "Sin título"),
            webpage_url=webpage_url,
            duration=entry.get("duration"),
            uploader=entry.get("uploader"),
            thumbnail=entry.get("thumbnail"),
            video_id=entry.get("id"),
        )

    def _create_media(
        self,
        data: dict
    ) -> Media:

        video_id = data.get("id")

        webpage_url = (
            data.get("webpage_url")
            or data.get("original_url")
            or data.get("url")
        )

        if webpage_url and not webpage_url.startswith("http"):
            webpage_url = (
                f"https://www.youtube.com/watch?v={webpage_url}"
            )

        if not webpage_url and video_id:
            webpage_url = (
                f"https://www.youtube.com/watch?v={video_id}"
            )

        return Media(
            title=data.get("title", "Sin título"),
            webpage_url=webpage_url or "",
            stream_url=None,
            duration=data.get("duration") or 0,
            thumbnail=data.get("thumbnail"),
            extractor=data.get("extractor", "youtube"),
            video_id=video_id,
        )