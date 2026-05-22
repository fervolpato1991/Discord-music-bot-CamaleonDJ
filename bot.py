import os
import asyncio
import discord
import yt_dlp
import logging
from dotenv import load_dotenv
from discord.ext import commands

# =========================
# CONFIG
# =========================

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

ffmpeg_before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
ffmpeg_options = {'options': '-vn'}

ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': False,
    'socket_timeout': 10,
}

ytdl_opts_playlist = {
    'quiet': True,
    'extract_flat': True,
    'skip_download': True,
}

ytdl = yt_dlp.YoutubeDL(ytdl_opts)

# =========================
# ESTADO GLOBAL
# =========================

queue = []
is_playing = False
volume = 0.5
now_playing_message = None
prefetch_cache = {}

# =========================
# LOGGING
# =========================

if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
# UTILIDADES
# =========================

def add_to_queue(url, title, requester):
    queue.append({"url": url, "title": title, "requester": requester})

def format_queue():
    if not queue:
        return "Vacía"
    text = ""
    for i, song in enumerate(queue[:5]):
        text += f"`{i+1}.` {song['title']}\n"
    if len(queue) > 5:
        text += f"... y {len(queue) - 5} más"
    return text

def progress_bar(current, total, length=20):
    if total == 0:
        return "🔘" + "▬" * (length - 1)
    progress = int(length * current / total)
    return "▬" * progress + "🔘" + "▬" * (length - progress)

def create_embed(data, title, url, requester):
    embed = discord.Embed(
        title="🎵 Reproduciendo ahora",
        description=f"[{title}]({url})",
        color=discord.Color.green()
    )
    if "thumbnail" in data:
        embed.set_thumbnail(url=data["thumbnail"])
    duration = data.get("duration", 0)
    if duration:
        embed.add_field(name="⏱️ Duración", value=f"{duration // 60}:{duration % 60:02d}")
        embed.add_field(name="⏱️ Progreso", value=progress_bar(0, duration), inline=False)
        embed.add_field(name="👤 Pedido por", value=requester.mention if requester else "Desconocido")
        embed.add_field(name="📜 Próximas canciones", value=format_queue(), inline=False)
    return embed

async def extract_info_safe(url):
    """
    Extrae la info de stream de una URL.
    Devuelve None si el video no está disponible o hay error,
    en lugar de lanzar una excepción que corta la cola.
    """
    try:
        data = await bot.loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)
        )
        return data
    except yt_dlp.utils.DownloadError as e:
        logger.warning(f"Video no disponible, saltando: {url} — {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado extrayendo info: {url} — {e}")
        return None

async def prefetch_next():
    """
    Pre-resuelve la URL de stream de la próxima canción en la cola
    mientras la actual sigue sonando, para que no haya pausa entre canciones.
    """
    if not queue:
        return
    next_song = queue[0]
    url = next_song["url"]
    if url not in prefetch_cache:
        logger.info(f"Pre-fetcheando: {next_song['title']}")
        data = await extract_info_safe(url)
        prefetch_cache[url] = data

# =========================
# UI
# =========================

class PlayerControls(discord.ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc
        self.update_buttons()

    def update_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "pause_resume":
                    if self.vc.is_paused():
                        item.label = "▶️"
                        item.style = discord.ButtonStyle.green
                    else:
                        item.label = "⏸️"
                        item.style = discord.ButtonStyle.grey

    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.grey, custom_id="pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
        elif self.vc.is_paused():
            self.vc.resume()
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.red)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing() or self.vc.is_paused():
            self.vc.stop()
        await interaction.response.defer()

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.grey)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        global is_playing
        vc = self.vc
        if vc:
            queue.clear()
            prefetch_cache.clear()
            is_playing = False
            vc.stop()
        await interaction.response.defer()

# =========================
# LÓGICA
# =========================

async def refresh_panel(ctx, embed, view):
    global now_playing_message
    try:
        if now_playing_message:
            await now_playing_message.delete()
    except Exception:
        pass
    now_playing_message = await ctx.send(embed=embed, view=view)

async def update_progress_bar(vc, message, duration):
    current = 0
    while current < duration:
        await asyncio.sleep(5)
        if vc.is_paused():
            continue
        if not vc.is_playing() and not vc.is_paused():
            break
        current += 5
        try:
            embed = message.embeds[0]
            embed.set_field_at(1, name="⏱️ Progreso", value=progress_bar(current, duration), inline=False)
            await message.edit(embed=embed)
        except Exception:
            break

async def update_queue_panel():
    global now_playing_message
    if not now_playing_message:
        return
    try:
        embed = now_playing_message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "📜 Próximas canciones":
                embed.set_field_at(i, name="📜 Próximas canciones", value=format_queue(), inline=False)
                break
        await now_playing_message.edit(embed=embed)
    except Exception:
        pass

async def play_next(ctx):
    global is_playing
    vc = ctx.voice_client

    if not vc or not vc.is_connected():
        is_playing = False
        return

    while queue:
        song = queue[0]
        url = song["url"]

        if url in prefetch_cache:
            data = prefetch_cache.pop(url)
        else:
            data = await extract_info_safe(url)

        if data is None:
            skipped = queue.pop(0)
            logger.info(f"Canción no disponible, saltada automáticamente: {skipped['title']}")
            continue

        queue.pop(0)
        is_playing = True

        title = song["title"]
        requester = song["requester"]

        stream_url = data.get("url")
        if not stream_url:
            for fmt in reversed(data.get("formats", [])):
                if fmt.get("acodec") != "none" and fmt.get("url"):
                    stream_url = fmt["url"]
                    break

        if not stream_url:
            logger.warning(f"No se encontró URL de stream para: {url}")
            continue

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                stream_url,
                executable=FFMPEG_PATH,
                before_options=ffmpeg_before_options,
                **ffmpeg_options
            ),
            volume=volume
        )

        def after_playing(error):
            if error:
                logger.error(f"Error durante reproducción: {error}")
            fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            try:
                fut.result()
            except Exception as e:
                logger.error(f"Error en after_playing: {e}")

        vc.play(source, after=after_playing)

        embed = create_embed(data, title, url, requester)
        view = PlayerControls(vc)
        await refresh_panel(ctx, embed, view)

        duration = data.get("duration", 0)
        if duration and now_playing_message:
            bot.loop.create_task(update_progress_bar(vc, now_playing_message, duration))

        bot.loop.create_task(prefetch_next())
        return

    is_playing = False
    if vc and vc.is_connected():
        bot.loop.create_task(auto_disconnect_if_idle(vc, delay=180))

async def auto_disconnect_if_idle(vc, delay=180):
    await asyncio.sleep(delay)
    try:
        if vc and vc.is_connected() and not vc.is_playing() and not queue:
            await vc.disconnect()
            logger.info("Desconectado por inactividad (cola vacía)")
    except Exception as e:
        logger.error(f"Auto-disconnect error: {e}")

async def disconnect_if_alone(vc, delay=60):
    global is_playing
    await asyncio.sleep(delay)
    try:
        if vc and vc.is_connected():
            members = [m for m in vc.channel.members if not m.bot]
            if len(members) == 0:
                if vc.is_playing() or vc.is_paused():
                    vc.stop()
                queue.clear()
                prefetch_cache.clear()
                is_playing = False
                await vc.disconnect()
                logger.info("Desconectado: canal vacío")
    except Exception as e:
        logger.error(f"disconnect_if_alone error: {e}")

async def delete_user_message_later(message, delay=10):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():
    logger.info(f"✅ Conectado como {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    vc = member.guild.voice_client
    if vc and vc.channel:
        members = [m for m in vc.channel.members if not m.bot]
        if len(members) == 0:
            bot.loop.create_task(disconnect_if_alone(vc))

# =========================
# COMANDOS
# =========================

@bot.command()
async def play(ctx, *, url):
    global is_playing

    if not ctx.voice_client:
        await ctx.invoke(join)

    bot.loop.create_task(delete_user_message_later(ctx.message, 10))

    is_playlist = "list=" in url

    try:
        if is_playlist:
            ytdl_playlist = yt_dlp.YoutubeDL(ytdl_opts_playlist)
            data = await bot.loop.run_in_executor(
                None, lambda: ytdl_playlist.extract_info(url, download=False)
            )
            count = 0
            for entry in data.get("entries", []):
                if not entry:
                    continue
                video_id = entry.get("id")
                if not video_id:
                    continue
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                add_to_queue(video_url, entry.get("title", "Sin título"), ctx.author)
                count += 1
            await ctx.send(f"📜 Playlist agregada: **{count}** canciones")
            await update_queue_panel()
        else:
            data = await bot.loop.run_in_executor(
                None, lambda: ytdl.extract_info(url, download=False)
            )
            add_to_queue(url, data["title"], ctx.author)
            await ctx.send(f"🎶 Agregado: **{data['title']}**")

    except Exception as e:
        await ctx.send(f"❌ Error al procesar: {e}")
        return

    if not is_playing:
        await play_next(ctx)
    else:
        await update_queue_panel()

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await ctx.send(embed=discord.Embed(
            description="⏭️ Canción saltada",
            color=discord.Color.red()
        ))
    else:
        await ctx.send("No hay nada reproduciéndose.")

@bot.command()
async def stop(ctx):
    global is_playing
    vc = ctx.voice_client
    if vc:
        queue.clear()
        prefetch_cache.clear()
        is_playing = False
        vc.stop()
        await ctx.send("⏹️ Detenido y cola vaciada.")

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send(embed=discord.Embed(
            description="⏸️ Canción pausada",
            color=discord.Color.orange()
        ))
    else:
        await ctx.send("No hay audio reproduciéndose.")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Reanudado")
    else:
        await ctx.send("No está en pausa.")

@bot.command()
async def leave(ctx):
    vc = ctx.voice_client
    if vc:
        queue.clear()
        prefetch_cache.clear()
        vc.stop()
        await vc.disconnect()

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("Tenés que estar en un canal de voz.")

@bot.command(name="queue")
async def queue_cmd(ctx):
    """Muestra la cola completa."""
    if not queue:
        await ctx.send("La cola está vacía.")
        return
    text = "\n".join([f"`{i + 1}.` {s['title']}" for i, s in enumerate(queue[:15])])
    if len(queue) > 15:
        text += f"\n... y {len(queue) - 15} más"
    embed = discord.Embed(title="📜 Cola de reproducción", description=text, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="vol")
async def volume_cmd(ctx, vol: int):
    """Ajusta el volumen (0-100). Ejemplo: !vol 80"""
    global volume
    if 0 <= vol <= 100:
        volume = vol / 100
        vc = ctx.voice_client
        if vc and vc.source:
            vc.source.volume = volume
        await ctx.send(f"🔊 Volumen ajustado a **{vol}%**")
    else:
        await ctx.send("El volumen debe estar entre **0** y **100**.")

@bot.command()
async def shutdown(ctx):
    with open("start.txt", "w") as f:
        f.write("OFF")
    await ctx.send("🔴 Bot apagando...")
    await bot.close()

# =========================

bot.run(os.getenv("DISCORD_TOKEN"))