from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Spotify
# ==========================================

SPOTIFY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

# ==========================================
# yt-dlp
# ==========================================

YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extract_flat": False,
    "source_address": "0.0.0.0",
    "socket_timeout": 15,
    "cache_dir": False,
}

# ==========================================
# FFmpeg
# ==========================================

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn",
}