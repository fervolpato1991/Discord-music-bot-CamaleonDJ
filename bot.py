import os
import asyncio
import discord
import yt_dlp
import logging
import sys
import spotipy
from dotenv import load_dotenv
from discord.ext import commands
from spotipy.oauth2 import SpotifyClientCredentials
from music.player import MusicPlayer
from music.services.youtube import YoutubeService

# =========================
# CONFIG
# =========================

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

spotify = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
)

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

queue = []
is_playing = False
volume = 0.5
now_playing_message = None
prefetch_cache = {}
player = MusicPlayer()
youtube = YoutubeService()

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

    if not queue:
        is_playing = False
        await asyncio.sleep(180)

        if not queue and vc and vc.is_connected() and not vc.is_playing():
            await vc.disconnect()
            await ctx.send("🔇 Me he desconectado del canal de voz debido a la inactividad.")
        return

    song = queue.pop(0)
    url = song["url"]

    try:
        media = await youtube.resolve_url(url)
        media = await youtube.resolve_stream(media)
        
    except Exception as e:
        logger.info(
            f"Canción no disponible, saltada automáticamente: "
            f"{song['title']} ({e})"
        )
        await play_next(ctx)
        return

    is_playing = True
    title = song["title"]
    requester = song["requester"]

    stream_url = media.stream_url
    
    if not stream_url:
        logger.warning(f"No se encontró URL de stream para: {url}")
        await play_next(ctx)
        return

    if vc.is_playing() or vc.is_paused():
        try:
            vc.stop()
        except Exception:
            pass

    try:
        raw_audio = discord.FFmpegPCMAudio(
            stream_url,
            executable=FFMPEG_PATH,
            before_options=ffmpeg_before_options,
            **ffmpeg_options
        )
        
        source = discord.PCMVolumeTransformer(raw_audio, volume=volume)

        def after_playing(error):
            if error:
                logger.error(f"Error durante reproducción: {error}")
            bot.loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(play_next(ctx), loop=bot.loop)
            )

        vc.play(source, after=after_playing)
        
        embed = create_embed(media, requester)
        view = PlayerControls(vc)
        await refresh_panel(ctx, embed, view)

        await prefetch_next()

    except Exception as e:
        logger.error(f"Error crítico al intentar reproducir {title}: {e}")
        is_playing = False
        await play_next(ctx)

    except Exception as e:
        logger.error(f"Error al intentar reproducir {title}: {e}")
        is_playing = False
        await play_next(ctx)

# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():
    logger.info(f"✅ Conectado como {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    global is_playing
    
    vc = member.guild.voice_client
    if not vc:
        return

    if len(vc.channel.members) == 1:
        logger.info(f"Bot se quedó solo en {vc.channel.name}. Desconectando...")
        queue.clear()
        prefetch_cache.clear()
        is_playing = False
        await vc.disconnect()
        return

    if member.id == bot.user.id and before.channel is not None and after.channel is None:
        logger.info("El bot fue desconectado manualmente. Limpiando estados.")
        queue.clear()
        prefetch_cache.clear()
        is_playing = False

# =========================
# COMANDOS
# =========================

@bot.command(name="play")
async def play(ctx, *, search: str):
    global is_playing
    
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

    # ==========================================
    # CASO A: ENLACES DE SPOTIFY (API PROXY PÚBLICA)
    # ==========================================
    if "spotify.com" in search:
        import aiohttp
        import re

        try:
            tracks_to_search = []
            spotify_title = "Lista de Spotify"

            match = re.search(r"spotify\.com/(playlist|album|track)/([a-zA-Z0-9]+)", search)
            if not match:
                await waiting_msg.edit(content="❌ Enlace de Spotify no reconocido.")
                return
                
            tipo = match.group(1)
            spotify_id = match.group(2)

            api_url = f"https://spotify.com{tipo}s/{spotify_id}/tracks" if tipo == "playlist" else f"https://spotify.com{tipo}s/{spotify_id}"
            
            if tipo == "track":
                api_url = f"https://spotify.comtracks/{spotify_id}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            proxy_url = f"https://spotify.com{tipo}/{spotify_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(proxy_url, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        await waiting_msg.edit(content="❌ No se pudo conectar con los servidores de Spotify.")
                        return
                    html = await response.text()

            raw_tracks = re.findall(r'\"name\":\"([^\"]+)\",\"artists\":\[\{\"name\":\"([^\"]+)\"', html)
             
            for t_name, a_name in raw_tracks:
                clean_title = t_name.encode().decode('utf-8', 'ignore')
                clean_artist = a_name.encode().decode('utf-8', 'ignore')
                tracks_to_search.append(f"{clean_title} {clean_artist}")

            tracks_to_search = list(dict.fromkeys(tracks_to_search))

            if not tracks_to_search:
                titles = re.findall(r'itemprop="name">([^<]+)<', html)
                if titles:
                    spotify_title = titles[0]
                    tracks_to_search = titles[1:]

            if not tracks_to_search:
                await waiting_msg.edit(content="❌ No se pudieron extraer canciones. Asegúrate de que la playlist sea pública.")
                return

            # REPRODUCCIÓN AUTOMÁTICA DE LA PRIMERA CANCIÓN
            primer_tema = tracks_to_search.pop(0)
            yt_data = await extract_info_safe(f"ytsearch1:{primer_tema}")
            
            if yt_data and 'entries' in yt_data and yt_data['entries']:
                video_data = yt_data['entries'][0]
                video_url = (
                    video_data.get("webpage_url")
                    or video_data.get("original_url")
                    or f"https://www.youtube.com/watch?v={video_data.get('id')}"
                )
                video_title = video_data.get('title', primer_tema)
                
                add_to_queue(video_url, video_title, ctx.author)
                
                if not vc.is_playing() and not vc.is_paused():
                    await play_next(ctx)
                    if not tracks_to_search:
                        await waiting_msg.delete()
                        return
                else:
                    if not tracks_to_search:
                        await waiting_msg.delete()
                        await ctx.send(f"✅ Añadida a la cola (vía Spotify): **{video_title}**")
                        await update_queue_panel()
                        return
            else:
                if not tracks_to_search:
                    await waiting_msg.edit(content="❌ No se pudo encontrar la canción en YouTube.")
                    return

            # TAREA EN SEGUNDO PLANO: ENCOLAR EL RESTO DE LAS CANCIONES
            async def procesar_playlist_background(lista_temas, mensaje_espera, nombre_lista):
                added_count = 1
                for track_name in lista_temas:
                    await asyncio.sleep(3.0) 
                    
                    yt_data_bg = await extract_info_safe(f"ytsearch1:{track_name}")
                    if yt_data_bg and 'entries' in yt_data_bg and yt_data_bg['entries']:
                        video_data_bg = yt_data_bg['entries'][0]
                        video_url_bg = (
                            video_data_bg.get("webpage_url")
                            or video_data_bg.get("original_url")
                            or f"https://www.youtube.com/watch?v={video_data_bg.get('id')}"
                        )
                        video_title_bg = video_data_bg.get('title', track_name)
                        
                        add_to_queue(video_url_bg, video_title_bg, ctx.author)
                        added_count += 1
                
                await update_queue_panel()
                try:
                    await mensaje_espera.delete()
                except Exception:
                    pass
                await ctx.send(f"🎶 ¡Se cargó la lista de Spotify! **{added_count}** canciones añadidas a la cola.")

            asyncio.create_task(procesar_playlist_background(tracks_to_search, waiting_msg, spotify_title))
            return

        except Exception as e:
            logger.error(f"Error procesando Spotify: {e}")
            await waiting_msg.edit(content="❌ Ocurrió un error inesperado al procesar Spotify.")
            return

    # ==========================================
    # CASO B: PLAYLISTS DE YOUTUBE
    # ==========================================
    elif "list=" in search:
        try:
            ydl_playlist = yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'skip_download': True})
            data = await bot.loop.run_in_executor(
                None, lambda: ydl_playlist.extract_info(search, download=False)
            )
            
            if not data or 'entries' not in data:
                await waiting_msg.edit(content="❌ No se pudo cargar la playlist o es privada.")
                return

            entries = list(data['entries'])
            added_count = 0
            
            for entry in entries:
                if entry:
                    video_url = (
                        video_data.get("webpage_url")
                        or video_data.get("original_url")
                        or f"https://www.youtube.com/watch?v={video_data.get('id')}"
                    )
                    title = entry.get('title', 'Canción de Playlist')
                    add_to_queue(video_url, title, ctx.author)
                    added_count += 1

            await waiting_msg.delete()
            await ctx.send(f"🎶 ¡Se añadieron **{added_count}** canciones desde la playlist: **{data.get('title', 'Desconocida')}**!")
            
            if not vc.is_playing() and not vc.is_paused():
                await play_next(ctx)
            else:
                await update_queue_panel()
            return

        except Exception as e:
            logger.error(f"Error cargando playlist: {e}")
            await waiting_msg.edit(content="❌ Ocurrió un error al procesar la lista de reproducción.")
            return

    # ==========================================
    # CASO C: BÚSQUEDA TRADICIONAL O VIDEO INDIVIDUAL DE YT
    # ==========================================
    else:
        # ------------------------------------------
        # # Video individual o búsqueda
        # # ------------------------------------------
        # 
        if "youtube.com" in search or "youtu.be" in search:
            media = await youtube.resolve_url(search)
        else:
            result = await youtube.search_first(search)
              
            if result is None:
                await waiting_msg.edit(content="❌ No se encontraron resultados.")
                return
              
            media = await youtube.resolve_url(result.webpage_url)

        video_url = media.webpage_url
        video_title = media.title
          
        add_to_queue(video_url, video_title, ctx.author)

        await waiting_msg.delete()

        if not vc.is_playing() and not vc.is_paused():
            await play_next(ctx)
        else:
            await ctx.send(f"✅ Añadida a la cola: **{video_title}**")
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
            
    queue.clear()
    prefetch_cache.clear()
    
    with open("start.txt", "w") as f:
        f.write("ON")
        
    await asyncio.sleep(3)   
    await bot.close()
    sys.exit(1)


# =========================

bot.run(os.getenv("DISCORD_TOKEN"))