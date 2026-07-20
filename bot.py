import os
import asyncio
import discord
import yt_dlp
import logging
import sys
from dotenv import load_dotenv
from discord.ext import commands
from urllib.parse import urlparse
from music.models import Song
from music.player import MusicPlayer
from music.services.music_services import MusicServices, MediaLoader

# =========================
# CONFIG
# =========================

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

ffmpeg_before_options = (
    '-reconnect 1 '
    '-reconnect_streamed 1 '
    '-reconnect_at_eof 1 '
    '-reconnect_delay_max 3 '
    '-hide_banner '
    '-loglevel error'
)

ffmpeg_options = {
    'options': (
        '-vn '
        '-f s16le '
        '-ar 48000 '
        '-ac 2'
    )
}

ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': 'in_playlist',
    'socket_timeout': 15,
    'source_address': '0.0.0.0',
    'cache_dir': False
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

player = MusicPlayer()
services = MusicServices()
loader = MediaLoader()

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

    player.queue.add(
        Song(
            title=title,
            webpage_url=url,
            requester=requester,
        )
    )

def format_queue():

    items = player.queue.as_list()

    if not items:
        return "Vacía"

    text = ""

    for i, song in enumerate(items[:5]):
        text += f"`{i+1}.` {song.title}\n"

    if len(items) > 5:
        text += f"... y {len(items) - 5} más"

    return text

def create_embed(media, requester):
    embed = discord.Embed(
        title="🎵 Reproduciendo ahora",
        description=f"[{media.title}]({media.webpage_url})",
        color=discord.Color.green()
    )

    if media.thumbnail:
        embed.set_thumbnail(url=media.thumbnail)

    if media.duration:
        embed.add_field(
            name="⏱️ Duración",
            value=f"{media.duration // 60}:{media.duration % 60:02d}"
        )

    embed.add_field(
        name="👤 Pedido por",
        value=requester.mention if requester else "Desconocido"
    )

    embed.add_field(
        name="📜 Próximas canciones",
        value=format_queue(),
        inline=False
    )

    return embed

async def extract_info_safe(url):

    try:

        return await bot.loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(
                url,
                download=False,
            ),
        )

    except yt_dlp.utils.DownloadError as e:

        logger.warning(
            f"Video no disponible: {url} ({e})"
        )

        return None

    except Exception as e:

        logger.exception(e)

        return None
async def prefetch_next():

    if player.queue.is_empty():
        return

    next_song = player.queue.peek()

    if next_song is None:
        return

    url = next_song.webpage_url

    if player.cache.has(url):
        return

    logger.info(
        f"Pre-fetcheando: {next_song.title}"
    )

    data = await extract_info_safe(url)

    if data is not None:

        player.cache.set(
            url,
            data,
        )
async def resolve_spotify_track(index, track, sem):

    async with sem:

        try:

            result = await services.youtube.search_first(
                f"{track.title} {track.artist}"
            )

            return (
                index,
                track,
                result,
            )

        except Exception as e:

            logger.warning(
                f"No se encontró: "
                f"{track.title} - {track.artist} ({e})"
            )

            return (
                index,
                track,
                None,
            )

async def handle_spotify(
    ctx,
    vc,
    waiting_msg,
    search,
):
    try:

        await waiting_msg.edit(
            content="🎵 Leyendo contenido de Spotify..."
        )

        spotify_tracks = await services.spotify.resolve(search)

        await waiting_msg.edit(
            content="🔍 Buscando canciones..."
        )

        added = 0
        started = False

        batch_size = 10

        # Si la playlist está vacía
        if not spotify_tracks:
            await waiting_msg.delete()
            await ctx.send("❌ No se encontró ninguna canción.")
            return

        # Comenzar a cargar el primer lote
        next_task = asyncio.create_task(
            loader.load_spotify_batch(
                spotify_tracks,
                0,
                batch_size,
            )
        )

        # Procesar todos los lotes excepto el último
        for start in range(
            batch_size,
            len(spotify_tracks),
            batch_size,
        ):

            media_list = await next_task

            # Mientras procesamos este lote,
            # comenzamos a cargar el siguiente.
            next_task = asyncio.create_task(
                loader.load_spotify_batch(
                    spotify_tracks,
                    start,
                    batch_size,
                )
            )

            for media in media_list:

                add_to_queue(
                    media.webpage_url,
                    media.title,
                    ctx.author,
                )

                added += 1

                if (
                    not started
                    and not vc.is_playing()
                    and not vc.is_paused()
                ):
                    started = True
                    asyncio.create_task(
                        play_next(ctx)
                    )

            await update_queue_panel()

        # Procesar el último lote pendiente
        media_list = await next_task

        for media in media_list:

            add_to_queue(
                media.webpage_url,
                media.title,
                ctx.author,
            )

            added += 1

            if (
                not started
                and not vc.is_playing()
                and not vc.is_paused()
            ):
                started = True
                asyncio.create_task(
                    play_next(ctx)
                )

        await update_queue_panel()

        await waiting_msg.delete()

        if added == 0:

            await ctx.send(
                "❌ No se encontró ninguna canción."
            )

            return

        await ctx.send(
            f"🎶 Se añadieron **{added}** canciones desde Spotify."
        )

        await update_queue_panel()

    except Exception:

        logger.exception(
            "Error procesando Spotify"
        )

        try:

            await waiting_msg.edit(
                content="❌ Error procesando Spotify."
            )

        except Exception:
            pass

async def handle_youtube_playlist(
    ctx,
    vc,
    waiting_msg,
    search,
):
    try:

        data = await bot.loop.run_in_executor(
            None,
            lambda: yt_dlp.YoutubeDL(
                {
                    "quiet": True,
                    "extract_flat": True,
                    "skip_download": True,
                }
            ).extract_info(
                search,
                download=False,
            ),
        )

        if not data or "entries" not in data:

            await waiting_msg.edit(
                content="❌ No se pudo cargar la playlist o es privada."
            )

            return

        entries = list(data["entries"])

        added = 0

        for entry in entries:

            if not entry:
                continue

            video_url = (
                entry.get("url")
                or entry.get("webpage_url")
                or f"https://www.youtube.com/watch?v={entry.get('id')}"
            )

            title = entry.get(
                "title",
                "Canción de Playlist",
            )

            add_to_queue(
                video_url,
                title,
                ctx.author,
            )

            added += 1

        await waiting_msg.delete()

        await ctx.send(
            f"🎶 ¡Se añadieron **{added}** canciones desde la playlist: **{data.get('title', 'Desconocida')}**!"
        )

        if not vc.is_playing() and not vc.is_paused():

            await play_next(ctx)

        else:

            await update_queue_panel()

    except Exception as e:

        logger.exception(e)

        try:

            await waiting_msg.edit(
                content="❌ Ocurrió un error al procesar la playlist."
            )

        except Exception:
            pass

async def handle_youtube_media(
    ctx,
    vc,
    waiting_msg,
    search,
):
    try:

        if "youtube.com" in search or "youtu.be" in search:

            media = await services.youtube.resolve_url(search)

        else:

            result = await services.youtube.search_first(search)

            if result is None:

                await waiting_msg.edit(
                    content="❌ No se encontraron resultados."
                )

                return

            media = await services.youtube.resolve_url(
                result.webpage_url
            )

        add_to_queue(
            media.webpage_url,
            media.title,
            ctx.author,
        )

        await waiting_msg.delete()

        if not vc.is_playing() and not vc.is_paused():

            await play_next(ctx)

        else:

            await ctx.send(
                f"✅ Añadida a la cola: **{media.title}**"
            )

            await update_queue_panel()

    except Exception as e:

        logger.exception(e)

        try:

            await waiting_msg.edit(
                content="❌ Error procesando la búsqueda."
            )

        except Exception:
            pass

# =========================
# UI
# =========================

class PlayerControls(discord.ui.View):

    def __init__(self, vc):

        super().__init__(timeout=None)

        self.vc = vc

        self.update_buttons()

    def get_vc(self):

        return player.voice_client if player.voice_client else self.vc

    def update_buttons(self):

        vc = self.get_vc()

        for item in self.children:

            if (
                isinstance(item, discord.ui.Button)
                and item.custom_id == "pause_resume"
            ):

                if vc and vc.is_paused():

                    item.label = "▶️"
                    item.style = discord.ButtonStyle.green

                else:

                    item.label = "⏸️"
                    item.style = discord.ButtonStyle.grey

    @discord.ui.button(
        label="⏸️",
        style=discord.ButtonStyle.grey,
        custom_id="pause_resume",
    )
    async def pause_resume(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        vc = self.get_vc()

        if vc is None:

            await interaction.response.defer()

            return

        if vc.is_playing():

            vc.pause()

        elif vc.is_paused():

            vc.resume()

        self.update_buttons()

        await interaction.response.edit_message(
            view=self
        )

    @discord.ui.button(
        label="⏭️",
        style=discord.ButtonStyle.red,
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        vc = self.get_vc()

        logger.info("BOTON SKIP")

        if vc:

            logger.info(f"is_playing={vc.is_playing()}")
            logger.info(f"is_paused={vc.is_paused()}")

            vc.stop()

            logger.info("vc.stop ejecutado")

        await interaction.response.defer()

    @discord.ui.button(
        label="⏹️",
        style=discord.ButtonStyle.grey,
    )
    async def stop_btn(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        vc = self.get_vc()

        if vc:

            player.queue.clear()
            player.cache.clear()

            vc.stop()

        await interaction.response.defer()

# =========================
# LÓGICA
# =========================

async def refresh_panel(ctx, embed, view):
    try:
        if player.panel_message:
            await player.panel_message.delete()
    except Exception:
        pass
    player.panel_message = await ctx.send(embed=embed, view=view)

async def update_queue_panel():

    if not player.panel_message:
        return
    try:
        embed = player.panel_message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "📜 Próximas canciones":
                embed.set_field_at(i, name="📜 Próximas canciones", value=format_queue(), inline=False)
                break
        await player.panel_message.edit(embed=embed)
    except Exception:
        pass

async def play_next(ctx):

    logger.info("========== PLAY_NEXT ==========")

    vc = ctx.voice_client

    if vc is None or not vc.is_connected():

        logger.info("No hay VoiceClient conectado.")

        player.current_song = None
        player.voice_client = None

        return

    while True:

        if player.queue.is_empty():

            logger.info("Cola vacía.")

            player.current_song = None

            await asyncio.sleep(180)

            if (
                player.queue.is_empty()
                and vc.is_connected()
                and not vc.is_playing()
                and not vc.is_paused()
            ):

                logger.info("Desconectando por inactividad.")

                await vc.disconnect()

                player.voice_client = None

                await ctx.send(
                    "🔇 Me he desconectado del canal de voz debido a la inactividad."
                )

            return

        song = player.queue.next()

        if song is None:

            logger.warning("queue.next() devolvió None.")

            continue

        logger.info(f"Reproduciendo: {song.title}")

        player.current_song = song

        try:

            media = await services.youtube.resolve_url(
                song.webpage_url
            )
            logger.info(media.webpage_url)

            media = await services.youtube.resolve_stream(
                media
            )

        except Exception as e:

            logger.warning(
                f"No se pudo cargar '{song.title}'. Saltando. ({e})"
            )

            continue

        if not media.stream_url:

            logger.warning(
                f"'{song.title}' no tiene stream."
            )

            continue

        try:

            raw_audio = discord.FFmpegPCMAudio(
                media.stream_url,
                executable=FFMPEG_PATH,
                before_options=ffmpeg_before_options,
                **ffmpeg_options
            )

            source = discord.PCMVolumeTransformer(
                raw_audio,
                volume=player.volume,
            )

        except Exception as e:

            logger.exception(
                f"No se pudo crear FFmpegAudio: {e}"
            )

            continue

        def after_playing(error):

            if error:

                logger.error(
                    f"Error reproduciendo: {error}"
                )

            future = asyncio.run_coroutine_threadsafe(
                play_next(ctx),
                bot.loop,
            )

            future.add_done_callback(
                lambda f: logger.exception(f.exception())
                if f.exception()
                else None
            )

        try:

            vc.play(
                source,
                after=after_playing,
            )

        except Exception as e:

            logger.exception(
                f"vc.play() falló: {e}"
            )

            continue

        player.voice_client = vc

        embed = create_embed(
            media,
            song.requester,
        )

        view = PlayerControls(vc)

        await refresh_panel(
            ctx,
            embed,
            view,
        )

        asyncio.create_task(
            prefetch_next()
        )

        return

# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():
    logger.info(f"✅ Conectado como {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):

    vc = member.guild.voice_client

    if not vc:
        return

    if len(vc.channel.members) == 1:
        logger.info(
            f"Bot se quedó solo en {vc.channel.name}. Desconectando..."
        )

        player.queue.clear()
        player.cache.clear()

        await vc.disconnect()
        return

    if (
        member.id == bot.user.id
        and before.channel is not None
        and after.channel is None
    ):
        logger.info(
            "El bot fue desconectado manualmente. Limpiando estados."
        )

        player.queue.clear()
        player.cache.clear()

# =========================
# COMANDOS
# =========================

@bot.command(name="play")
async def play(ctx, *, search: str):   
    
    if not ctx.author.voice:
        await ctx.send("❌ ¡Debes estar en un canal de voz para escuchar música!")
        return

    vc = ctx.voice_client
    if not vc:
        try:
            vc = await ctx.author.voice.channel.connect()
        except Exception as e:
            await ctx.send(f"❌ No pude conectarme al canal de voz: {e}")
            return

    waiting_msg = await ctx.send("🔍 Analizando enlace o búsqueda...")
    search = search.strip("<>").strip()

    if "spotify.com" in search:
        
        await handle_spotify(
            ctx,
            vc,
            waiting_msg,
            search,
        )

        return

    elif "list=" in search:
        
        await handle_youtube_playlist(
            ctx,
            vc,
            waiting_msg,
            search,
        )

        return

    else:
        await handle_youtube_media(
            ctx,
            vc,
            waiting_msg,
            search,
        )
        
        return

@bot.command()
async def skip(ctx):

    vc = ctx.voice_client

    if vc:

        logger.info(f"is_playing={vc.is_playing()}")

        logger.info(f"is_paused={vc.is_paused()}")

        player.stopping = True

        vc.stop()

        logger.info("vc.stop ejecutado")

@bot.command()
async def stop(ctx):

    vc = ctx.voice_client

    if vc:

        player.stopping = True

        player.queue.clear()

        player.cache.clear()

        vc.stop()

        await ctx.send(
            "⏹️ Detenido y cola vaciada."
        )

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
        player.queue.clear()
        player.cache.clear()
        player.stopping = True
        vc.stop()
        await vc.disconnect()

@bot.command(name="queue")
async def queue_cmd(ctx):
    """Muestra la cola completa."""
    items = player.queue.as_list()
    
    if not items:
        await ctx.send("La cola está vacía.")
        return
    
    text = "\n".join(
    [
        f"`{i + 1}.` {s['title']}"
        for i, s in enumerate(items[:15])
    ]
)

    if len(items) > 15:
        text += f"\n... y {len(items) - 15} más"
    embed = discord.Embed(title="📜 Cola de reproducción", description=text, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="vol")
async def volume_cmd(ctx, vol: int):
    """Ajusta el volumen (0-100). Ejemplo: !vol 80"""

    if 0 <= vol <= 100:

        player.volume = vol / 100

        vc = ctx.voice_client

        if vc and vc.source:
            vc.source.volume = player.volume

        await ctx.send(
            f"🔊 Volumen ajustado a **{vol}%**"
        )

    else:

        await ctx.send(
            "El volumen debe estar entre **0** y **100**."
        ) 

@bot.command()
async def shutdown(ctx):
    await ctx.send("🔴 Apagando CamaleonDJ...")
    logger.info("Apagado completo solicitado por el dueño.")
    
    if ctx.voice_client:
        try: await ctx.voice_client.disconnect()
        except Exception: pass
        
    with open("start.txt", "w") as f:
        f.write("OFF")
        
    await bot.close()
    sys.exit(0)

@bot.command()
async def restart(ctx):
    await ctx.send("🔄 Reiniciando el servicio... Dame unos segundos.")
    logger.info("Reinicio manual del servicio solicitado.")
    
    if ctx.voice_client:
        try:
            logger.info("Desconectando activamente del canal de voz antes del reinicio.")
            await ctx.voice_client.disconnect(force=True)
        except Exception as e:
            logger.error(f"No se pudo desconectar el canal de voz en el reinicio: {e}")
            
    player.queue.clear()
    player.cache.clear()
    
    with open("start.txt", "w") as f:
        f.write("ON")
        
    await asyncio.sleep(3)   
    await bot.close()
    sys.exit(1)

@bot.command()
async def shuffle(ctx):

    if player.queue.is_empty():
        await ctx.send("❌ La cola está vacía.")
        return

    player.queue.shuffle()

    await update_queue_panel()

    await ctx.send("🔀 Cola mezclada.")

@bot.command()
async def remove(ctx, position: int):

    if player.queue.is_empty():
        await ctx.send("❌ La cola está vacía.")
        return

    position -= 1

    song = player.queue.remove(position)

    if song is None:
        await ctx.send("❌ Esa posición no existe.")
        return

    await update_queue_panel()

    await ctx.send(
        f"🗑 Eliminada de la cola:\n**{song.title}**"
    )

@bot.command()
async def move(
    ctx,
    origin: int,
    destination: int,
):

    if player.queue.is_empty():
        await ctx.send("❌ La cola está vacía.")
        return

    origin -= 1
    destination -= 1

    moved = player.queue.move(
        origin,
        destination,
    )

    if moved is None:
        await ctx.send("❌ Posición inválida.")
        return

    await update_queue_panel()

    await ctx.send(
        f"📦 Canción movida a la posición {destination + 1}."
    )

@bot.command()
async def jump(ctx, position: int):

    if player.queue.is_empty():
        await ctx.send("❌ La cola está vacía.")
        return

    result = player.queue.jump(position - 1)

    if result is None:
        await ctx.send("❌ Esa posición no existe.")
        return

    song, skipped = result

    await update_queue_panel()

    vc = ctx.voice_client

    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()

    await ctx.send(
        f"⏩ Saltando a **{song.title}**"
    )


# =========================

bot.run(os.getenv("DISCORD_TOKEN"))