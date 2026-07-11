from __future__ import annotations

import random

from collections import deque
from typing import Iterable


class QueueManager:

    def __init__(self):

        self._queue = deque()

    def __len__(self):
        return len(self._queue)
    
    def __iter__(self):
        return iter(self._queue)

    # ==================================================
    # Agregar canciones
    # ==================================================

    def add(self, item):

        self._queue.append(item)

    def add_many(
        self,
        items: Iterable,
    ):

        self._queue.extend(items)

    # ==================================================
    # Obtener canciones
    # ==================================================

    def next(self):

        if self._queue:
            return self._queue.popleft()

        return None

    def peek(self):

        if self._queue:
            return self._queue[0]

        return None

    def items(self):

        return list(self._queue)

    # ==================================================
    # Estado
    # ==================================================

    def size(self):

        return len(self._queue)

    def empty(self):

        return len(self._queue) == 0

    # ==================================================
    # Modificaciones
    # ==================================================

    def clear(self):

        self._queue.clear()

    def shuffle(self):

        data = list(self._queue)

        random.shuffle(data)

        self._queue = deque(data)

    def remove(self, index: int):

        if index < 0 or index >= self.size():
            return None

        data = list(self._queue)

        value = data.pop(index)

        self._queue = deque(data)

        return value

    def move(
        self,
        old_index: int,
        new_index: int,
    ):
        
        if old_index < 0 or old_index >= self.size():
            return None

        if new_index < 0 or new_index >= self.size():
            return None

        data = list(self._queue)

        song = data.pop(old_index)

        data.insert(new_index, song)

        self._queue = deque(data)

        return song

    def jump(
        self,
        index: int,
    ):
        if index < 0 or index >= self.size():
            return None

        data = list(self._queue)
        
        skipped = data[:index]
        
        selected = data[index]
        
        self._queue = deque(data[index:])
        
        return selected, skipped