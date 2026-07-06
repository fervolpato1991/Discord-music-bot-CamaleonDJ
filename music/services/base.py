from __future__ import annotations

from abc import ABC, abstractmethod

from music.models import Song


class MusicService(ABC):
    """
    Clase base para cualquier proveedor de música.
    """

    @abstractmethod
    async def get_song(self, query: str) -> Song:
        ...

    @abstractmethod
    async def search(self, query: str) -> list[Song]:
        ...