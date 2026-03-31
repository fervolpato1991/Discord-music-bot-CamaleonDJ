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
    'format': 'bestaudio',
    'outtmpl': 'song.%(ext)s',
    'quiet': True,
    'noplaylist': True
}

ffmpeg_options = {
    'before_options': (
        '-reconnect 1 '
        '-reconnect_streamed 1 '
        '-reconnect_delay_max 5 '
        '-nostdin'
    ),
    'options': (
        '-vn '
        '-ac 2 '
        '-ar 48000 '
        '-af "aresample=async=1,volume=1.2"'
    )
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
    vc = ctx.voice_client

    if not vc:
        await ctx.invoke(join)
        vc = ctx.voice_client

    await ctx.send("⏳ Descargando...")

    loop = bot.loop

    def download():
        return ytdl.extract_info(url, download=True)

    data = await loop.run_in_executor(None, download)
    filename = ytdl.prepare_filename(data)

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(
            filename,
            executable=FFMPEG_PATH,
            options='-vn'
        ),
        volume=1.0
    )

    if vc.is_playing():
        vc.stop()

    vc.play(source)

    for file in os.listdir():
        if file.startswith("song.") and file != filename:
            os.remove(file)

    await ctx.send(f"Reproduciendo: {data['title']}")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Pausado")
    else:
        await ctx.send("No hay audio reproduciéndose")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Reanudado")
    else:
        await ctx.send("No está en pausa")

@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    if vc:
        vc.stop()
        await ctx.send("⏹️ Detenido")

@bot.command()
async def shutdown(ctx):
    await ctx.send("Apagando bot...")

    vc = ctx.voice_client
    if vc:
        vc.stop()
        await vc.disconnect()

    await bot.close()

bot.run(os.getenv("DISCORD_TOKEN"))