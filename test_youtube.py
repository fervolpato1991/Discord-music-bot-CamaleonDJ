import asyncio

from music.services.youtube import YoutubeService


async def main():

    yt = YoutubeService()

    results = await yt.search("Queen Bohemian Rhapsody")

    media = await yt.resolve_url(results[0].webpage_url)

    print("Antes:")
    print(media.stream_url)

    media = await yt.resolve_stream(media)

    print()

    print("Después:")
    print(media.stream_url)

    print()

    print(media.stream_url[:120])
    
    playlist = await yt.resolve_playlist(
    "https://youtube.com/playlist?list=PLIBk2SAEr-aEVAUkEUbGWN0JUQhyqQiTA&si=tXdCjBuCeds6AkVq"
    )
    
    print()
    
    print("Playlist:")
    
    print(len(playlist))
    
    print()
    
    for media in playlist[:5]:
        print(media.title)


asyncio.run(main())