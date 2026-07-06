from __future__ import annotations

from typing import Optional

import discord

from .cache import MusicCache
from .models import Song
from .queue import MusicQueue


class MusicPlayer:
    def __init__(self) -> None:
        self.queue: MusicQueue = MusicQueue()
        self.cache: MusicCache = MusicCache()

        self.current_song: Song | None = None
        self.voice_client: discord.VoiceClient | None = None

        self.loop: bool = False
        self.loop_queue: bool = False

        self.volume: float = 0.50

        self.idle: bool = True