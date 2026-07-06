from dataclasses import dataclass, field
from typing import Any
from enum import Enum

import discord


class SongSource(str, Enum):
    """
    Plataformas soportadas por el bot.
    """

    YOUTUBE = "youtube"
    SPOTIFY = "spotify"
    SOUNDCLOUD = "soundcloud"
    LOCAL = "local"
    DIRECT = "direct"

@dataclass(slots=True)

class Song:
    """
    Representa una canción independientemente de su origen.
    """

    title: str

    webpage_url: str

    requester: discord.Member | None

    source: SongSource = SongSource.YOUTUBE

    artist: str | None = None

    duration: int | None = None

    thumbnail: str | None = None

    stream_url: str | None = None

    spotify_url: str | None = None

    spotify_id: str | None = None

    youtube_id: str | None = None

    requested_query: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)

class Media:

    title: str

    webpage_url: str

    stream_url: str | None = None

    duration: int = 0

    thumbnail: str | None = None

    extractor: str = "youtube"
    
    video_id: str | None = None

@dataclass(slots=True)

class SearchResult:

    title: str

    webpage_url: str

    duration: int | None

    uploader: str | None

    thumbnail: str | None

    video_id: str | None