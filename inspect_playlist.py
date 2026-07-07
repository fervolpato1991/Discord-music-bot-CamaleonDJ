import asyncio
from spotify_scraper import AsyncSpotifyClient

URL = "https://open.spotify.com/playlist/37i9dQZF1DX2VvACCrgjrt"

async def main():

    async with AsyncSpotifyClient() as client:
        playlist = await client.get_playlist(URL)

    print(type(playlist))
    print(dir(playlist))

    print(type(playlist.tracks))
    print(len(playlist.tracks))

    first = playlist.tracks[0]

    print(type(first))
    print(dir(first))

asyncio.run(main())