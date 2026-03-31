import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import yt_dlp
import time
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"

queue = []
is_playing = False

ytdl_format_options = {
    'format': 'bestaudio[ext=webm]/bestaudio',
    'outtmpl': 'song_%(id)s.%(ext)s',
    'quiet': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'no_warnings': True
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

async def play_next(ctx):
    global is_playing

    if len(queue) > 0:
        is_playing = True
        url = queue.pop(0)

        vc = ctx.voice_client

        loop = bot.loop

        def download():
            return ytdl.extract_info(url, download=True)

        data = await loop.run_in_executor(None, download)
        filename = ytdl.prepare_filename(data)

        vc.current_file = filename

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                filename,
                executable=FFMPEG_PATH,
                options='-vn'
            ),
            volume=1.0
        )

        def after_playing(error):
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except:
                pass

            fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            try:
                fut.result()
            except:
                pass

        vc.play(source, after=after_playing)

        await ctx.send(f"🎶 Reproduciendo: {data['title']}")

    else:
        is_playing = False

@bot.command()
async def queue_list(ctx):
    if len(queue) == 0:
        await ctx.send("📭 Cola vacía")
    else:
        msg = "\n".join([f"{i+1}. {url}" for i, url in enumerate(queue)])
        await ctx.send(f"📜 Cola:\n{msg}")

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
async def start(ctx):
    try:
        with open("start.txt", "w") as f:
            f.write("ON")

        await ctx.send("🟢 Bot configurado para encenderse")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def play(ctx, *, url):
    global is_playing

    if not ctx.voice_client:
        await ctx.invoke(join)

    queue.append(url)

    await ctx.send("➕ Canción agregada a la cola")

    if not is_playing:
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client

    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Saltando canción...")

@bot.command()
async def leave(ctx):
    vc = ctx.voice_client

    if vc:
        vc.stop()

        if hasattr(vc, "current_file"):
            try:
                if os.path.exists(vc.current_file):
                    os.remove(vc.current_file)
                    print("Archivo borrado (leave)")
            except Exception as e:
                print(f"Error borrando: {e}")

        await vc.disconnect()

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

        if hasattr(vc, "current_file"):
            try:
                if os.path.exists(vc.current_file):
                    os.remove(vc.current_file)
                    print("Archivo borrado (stop)")
            except Exception as e:
                print(f"Error borrando: {e}")

        await ctx.send("⏹️ Detenido")

@bot.command()
async def shutdown(ctx):
    try:
        with open("start.txt", "w") as f:
            f.write("OFF")

        await ctx.send("🔴 Apagando bot...")
        await bot.close()
    except Exception as e:
        await ctx.send(f"Error: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))