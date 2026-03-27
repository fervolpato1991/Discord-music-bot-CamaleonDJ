import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import yt_dlp

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"

ytdl_format_options = {
    'format': 'bestaudio[ext=webm]/bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'http_chunk_size': 1048576,
    'extractor_args': {
        'youtube': {
            'player_client': ['android'] 
        }
    }
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("No estás en un canal de voz")

@bot.command()
async def play(ctx, *, url):
    if not ctx.voice_client:
        await ctx.invoke(join)

    loop = bot.loop
    data = await loop.run_in_executor(
        None,
        lambda: ytdl.extract_info(url, download=False)
    )

   
    if 'entries' in data:
        data = data['entries'][0]

    stream_url = data['url']

    source = await discord.FFmpegOpusAudio.from_probe(
        stream_url,
        executable=FFMPEG_PATH,
        method="fallback",  
        **ffmpeg_options
    )

    ctx.voice_client.play(source)

    await ctx.send(f"Reproduciendo: {data['title']}")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

bot.run(os.getenv("DISCORD_TOKEN"))