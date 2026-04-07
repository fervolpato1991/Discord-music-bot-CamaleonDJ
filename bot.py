import os
import time
import asyncio
import discord
import yt_dlp
from dotenv import load_dotenv
from discord.ext import commands

# =========================
# CONFIG
# =========================

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"

ffmpeg_options = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl_opts = {
    'format': 'bestaudio[ext=webm]/bestaudio',
    'outtmpl': 'song_%(id)s.%(ext)s',
    'quiet': True,
    'noplaylist': False,
    'extract_flat': False
}

ytdl_opts_playlist = {
    'quiet': True,
    'extract_flat': True,
    'skip_download': True
}

ytdl = yt_dlp.YoutubeDL(ytdl_opts)

# =========================
# ESTADO GLOBAL
# =========================

queue = []
is_playing = False
volume = 0.5
now_playing_message = None

# =========================
# UTILIDADES
# =========================

def add_to_queue(url, title, requester):
    queue.append({
        "url": url,
        "title": title,
        "requester": requester
    })

def safe_delete(file, retries=5, delay=1):
    for _ in range(retries):
        try:
            if file and os.path.exists(file):
                os.remove(file)
                return
        except:
            time.sleep(delay)

def cleanup_current(vc):
    if hasattr(vc, "current_file"):
        safe_delete(vc.current_file)

def cleanup_temp_files(active_file=None):
    for file in os.listdir():
        if file.endswith(".webm"):
            if active_file and file == active_file:
                continue
            safe_delete(file)

def format_queue():
    if not queue:
        return "Vacía"

    text = ""
    for i, song in enumerate(queue[:5]):
        text += f"`{i+1}.` {song['title']}\n"

    if len(queue) > 5:
        text += f"... y {len(queue)-5} más"

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
        embed.add_field(name="⏱️ Duración", value=f"{duration//60}:{duration%60:02}")
        embed.add_field(name="⏱️ Progreso", value=progress_bar(0, duration), inline=False)
        embed.add_field(name="👤 Pedido por", value=requester.mention if requester else "Desconocido")
        embed.add_field(name="📜 Próximas canciones", value=format_queue(), inline=False)

    return embed

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
        if self.vc.is_playing():
            self.vc.stop()
            
        await interaction.response.defer()

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.grey)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc
        
        if vc:
            vc.stop()
            
            await asyncio.sleep(1)
            
            global is_playing, queue
            is_playing = False
            queue.clear()
            
            if hasattr(vc, "current_file"):
                safe_delete(vc.current_file)
                
        await interaction.response.defer()

# =========================
# LÓGICA
# =========================

async def refresh_panel(ctx, embed, view):
    global now_playing_message
    try:
        if now_playing_message:
            await now_playing_message.delete()
    except:
        pass

    now_playing_message = await ctx.send(embed=embed, view=view)

async def update_progress_bar(vc, message, duration):
    current = 0
    while vc.is_playing() and current < duration:
        await asyncio.sleep(5)
        current += 5
        try:
            embed = message.embeds[0]
            embed.set_field_at(1, name="⏱️ Progreso", value=progress_bar(current, duration), inline=False)
            await message.edit(embed=embed)
        except:
            break

async def update_queue_panel():
    global now_playing_message

    if not now_playing_message:
        return

    try:
        embed = now_playing_message.embeds[0]

        for i, field in enumerate(embed.fields):
            if field.name == "📜 Próximas canciones":
                embed.set_field_at(
                    i,
                    name="📜 Próximas canciones",
                    value=format_queue(),
                    inline=False
                )
                break

        await now_playing_message.edit(embed=embed)

    except:
        pass

async def play_next(ctx):
    global is_playing
    vc = ctx.voice_client

    if not ctx.voice_client:
        return

    if queue:
        is_playing = True
        song = queue.pop(0)

        url = song["url"]
        title = song["title"]
        requester = song["requester"]

        data = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
        filename = ytdl.prepare_filename(data)

        vc.current_file = filename

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH, **ffmpeg_options),
            volume=volume
        )

        def after_playing(error, file_to_delete=filename):
            safe_delete(file_to_delete)
            fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            try:
                fut.result()
            except:
                pass

        vc.play(source, after=after_playing)

        embed = create_embed(data, title, url, requester)
        view = PlayerControls(vc)

        await refresh_panel(ctx, embed, view)
        bot.loop.create_task(update_progress_bar(vc, now_playing_message, data.get("duration", 0)))

    else:
        is_playing = False
        if vc:
            bot.loop.create_task(auto_disconnect_if_idle(vc, delay=60))

async def auto_cleanup_loop():
    await bot.wait_until_ready()

    while True:
        try:
            vc = None

            for guild in bot.guilds:
                if guild.voice_client:
                    vc = guild.voice_client
                    break

            active_file = None
            if vc and hasattr(vc, "current_file"):
                active_file = vc.current_file

            cleanup_temp_files(active_file)

        except Exception as e:
            print(f"Error en auto cleanup: {e}")

        await asyncio.sleep(30)

async def disconnect_if_alone(vc, delay=60):
    global is_playing, queue

    await asyncio.sleep(delay)

    try:
        if vc and vc.is_connected():
            members = [m for m in vc.channel.members if not m.bot]

            if len(members) == 0:
                if vc.is_playing() or vc.is_paused():
                    vc.stop()

                queue.clear()
                is_playing = False

                await vc.disconnect()
                print("🔌 Desconectado por inactividad")

    except Exception as e:
        print(e)

async def auto_disconnect_if_idle(vc, delay=180):
    await asyncio.sleep(delay)

    try:
        if vc and vc.is_connected():
            if not vc.is_playing():
                if len(queue) == 0:
                    await vc.disconnect()
                    print("🔌 Desconectado por inactividad")
    except Exception as e:
        print(f"Auto-disconnect error: {e}")


async def delete_user_message_later(message, delay=10):
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except:
            pass

# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():
    print(f"✅ Conectado como {bot.user}")
    cleanup_temp_files()
    bot.loop.create_task(auto_cleanup_loop())

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

    loop = bot.loop
    
    bot.loop.create_task(delete_user_message_later(ctx.message, 10))

    is_playlist = "list=" in url

    try:
        if is_playlist:
            ytdl_playlist = yt_dlp.YoutubeDL({
                'quiet': True,
                'extract_flat': True,
                'skip_download': True
            })

            data = await loop.run_in_executor(
                None,
                lambda: ytdl_playlist.extract_info(url, download=False)
            )

            count = 0

            for entry in data.get("entries", []):
                if not entry:
                    continue

                video_id = entry.get("id")
                if not video_id:
                    continue

                video_url = f"https://www.youtube.com/watch?v={video_id}"

                add_to_queue(
                    video_url,
                    entry.get("title", "Sin título"),
                    ctx.author
                )

                count += 1

            await ctx.send(f"📜 Playlist agregada: {count} canciones")
        
        if is_playlist:
            await update_queue_panel()

        else:
            data = await loop.run_in_executor(
                None,
                lambda: ytdl.extract_info(url, download=False)
            )

            add_to_queue(url, data["title"], ctx.author)

            await ctx.send(f"🎶 Agregado: {data['title']}")
            

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
    if vc and vc.is_playing():
        vc.stop()
        await asyncio.sleep(1)

        if hasattr(vc, "current_file"):
            safe_delete(vc.current_file)

        await ctx.send(embed=discord.Embed(
            description="⏭️ Canción saltada",
            color=discord.Color.red()
        ))


@bot.command()
async def stop(ctx):
    global is_playing
    vc = ctx.voice_client
    if vc:
        vc.stop()
        queue.clear()
        is_playing = False
        cleanup_current(vc)
        await ctx.send("⏹️ Detenido")

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client

    if vc and vc.is_playing():
        vc.pause()
        await ctx.send(embed= discord.Embed(
            description="⏸️ Canción pausada",
            color=discord.Color.red()
        ))
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
async def leave(ctx):
    vc = ctx.voice_client
    if vc:
        vc.stop()
        queue.clear()
        cleanup_current(vc)
        await vc.disconnect()

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()

@bot.command()
async def shutdown(ctx):
    with open("start.txt", "w") as f:
        f.write("OFF")
    await ctx.send("🔴 Bot apagando")
    await bot.close()

@bot.command()
async def start(ctx):
    with open("start.txt", "w") as f:
        f.write("ON")
    await ctx.send("🟢 Bot iniciado")
    await bot.start()

# =========================

bot.run(os.getenv("DISCORD_TOKEN"))