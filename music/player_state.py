from __future__ import annotations

import discord


class PlayerState:

    def __init__(self):

        self.is_playing: bool = False

        self.volume: float = 0.5

        self.now_playing_message: discord.Message | None = None

        self.prefetch_cache: dict = {}