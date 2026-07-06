from enum import Enum
from urllib.parse import urlparse


class ServiceType(Enum):
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"
    SEARCH = "search"
    DIRECT = "direct"


class ServiceRouter:

    @staticmethod
    def resolve(query: str) -> ServiceType:

        query = query.strip()

        if "spotify.com" in query:
            return ServiceType.SPOTIFY

        if "youtube.com" in query or "youtu.be" in query:
            return ServiceType.YOUTUBE

        if query.startswith("http"):
            return ServiceType.DIRECT

        return ServiceType.SEARCH