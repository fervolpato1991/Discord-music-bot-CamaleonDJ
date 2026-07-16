from __future__ import annotations

import random

from collections import deque
from typing import Any, Iterable


class MusicQueue:

    def __init__(self):
        self._songs = deque()

    # ==================================================
    # Métodos especiales
    # ==================================================

    def __len__(self):
        return len(self._songs)

    def __iter__(self):
        return iter(self._songs)

    # ==================================================
    # Agregar canciones
    # ==================================================

    def add(
        self,
        song: Any,
    ) -> None:

        self._songs.append(song)

    def add_many(
        self,
        songs: Iterable[Any],
    ) -> None:

        self._songs.extend(songs)

    def insert_front(
        self,
        song: Any,
    ) -> None:

        self._songs.appendleft(song)

    # ==================================================
    # Obtener canciones
    # ==================================================

    def next(self) -> Any | None:

        if not self._songs:
            return None

        return self._songs.popleft()

    def peek(self) -> Any | None:

        if not self._songs:
            return None

        return self._songs[0]

    def as_list(self) -> list[Any]:

        return list(self._songs)

    # ==================================================
    # Estado
    # ==================================================

    def is_empty(self) -> bool:

        return len(self._songs) == 0

    def size(self) -> int:

        return len(self._songs)

    # ==================================================
    # Modificaciones
    # ==================================================

    def clear(self) -> None:

        self._songs.clear()

    def shuffle(self) -> None:

        songs = list(self._songs)

        random.shuffle(songs)

        self._songs = deque(songs)

    def remove(
        self,
        index: int,
    ) -> Any | None:

        if index < 0 or index >= len(self):
            return None

        songs = list(self._songs)

        song = songs.pop(index)

        self._songs = deque(songs)

        return song

    def move(
        self,
        old_index: int,
        new_index: int,
    ) -> Any | None:

        if old_index < 0 or old_index >= len(self):
            return None

        if new_index < 0 or new_index >= len(self):
            return None

        songs = list(self._songs)

        song = songs.pop(old_index)

        songs.insert(new_index, song)

        self._songs = deque(songs)

        return song

    def jump(
        self,
        index: int,
    ) -> tuple[Any, list[Any]] | None:

        if index < 0 or index >= len(self):
            return None

        songs = list(self._songs)

        skipped = songs[:index]

        selected = songs[index]

        self._songs = deque(songs[index:])

        return selected, skipped