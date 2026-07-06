from collections import deque
import random

from .models import Song


class MusicQueue:

    def __init__(self):
        self._songs = deque()

    def add(self, song: Song) -> None:
        self._songs.append(song)

    def next(self) -> Song | None:
        if not self._songs:
            return None
        return self._songs.popleft()

    def peek(self) -> Song | None:
        return self._songs[0] if self._songs else None

    def clear(self) -> None:
        self._songs.clear()

    def shuffle(self) -> None:
        songs = list(self._songs)
        random.shuffle(songs)
        self._songs = deque(songs)

    def remove(self, index: int) -> Song:
        songs = list(self._songs)
        song = songs.pop(index)
        self._songs = deque(songs)
        return song

    def insert_front(self, song: Song) -> None:
        self._songs.appendleft(song)

    def as_list(self) -> list[Song]:
        return list(self._songs)

    def is_empty(self) -> bool:
        return len(self._songs) == 0

    def __len__(self) -> int:
        return len(self._songs)

    def __iter__(self):
        return iter(self._songs)