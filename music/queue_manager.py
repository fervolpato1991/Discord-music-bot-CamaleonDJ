from __future__ import annotations

from collections import deque
from typing import Iterable


class QueueManager:

    def __init__(self):

        self._queue = deque()

    def add(self, item):

        self._queue.append(item)

    def add_many(
        self,
        items: Iterable,
    ):

        self._queue.extend(items)

    def next(self):

        if self._queue:
            return self._queue.popleft()

        return None

    def peek(self):

        if self._queue:
            return self._queue[0]

        return None

    def clear(self):

        self._queue.clear()

    def size(self):

        return len(self._queue)

    def empty(self):

        return len(self._queue) == 0

    def items(self):

        return list(self._queue)

    def remove(self, index: int):

        data = list(self._queue)

        value = data.pop(index)

        self._queue = deque(data)

        return value