import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import time

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
now_playing_message = None

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"

queue = []
is_playing = False
volume = 0.5

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

def cleanup_temp_files():
    for file in os.listdir():
        if file.endswith(".webm"):
            safe_delete(file)

def safe_delete(file, retries=5, delay=1):
    for i in range(retries):
        try:
            if file and os.path.exists(file):
                os.remove(file)
                print(f"🧹 Borrado: {file}")
                return
        except Exception as e:
            print(f"Intento {i+1} fallido al borrar: {e}")
            time.sleep(delay)

    print(f"❌ No se pudo borrar: {file}")

def format_queue():
    if len(queue) == 0:
        return "Vacía"

    text = ""
    for i, song in enumerate(queue[:5]):  # mostramos solo 5
        text += f"`{i+1}.` {song['title']}\n"

    if len(queue) > 5:
        text += f"... y {len(queue)-5} más"

    return text

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

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
        if self.vc:
            self.vc.stop()
        await interaction.response.defer()

def progress_bar(current, total, length=20):
    if total == 0:
        return "🔘" + "▬" * (length - 1)

    progress = int(length * current / total)
    bar = "▬" * progress + "🔘" + "▬" * (length - progress)
    return bar

async def update_progress_bar(vc, message, duration):
    current = 0

    while vc.is_playing() and current < duration:
        await asyncio.sleep(5)
        current += 5

        try:
            embed = message.embeds[0]

            embed.set_field_at(
                1,  # IMPORTANTE: posición del campo progreso
                name="⏱️ Progreso",
                value=progress_bar(current, duration),
                inline=False
            )

            await message.edit(embed=embed)

        except:
            break

async def play_next(ctx):
    global is_playing

    if len(queue) > 0:
        is_playing = True
        song = queue.pop(0)
        url = song["url"]
        title = song["title"]
   
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
            volume=volume
        )

        def after_playing(error):
            if error:
                print(f"Error en reproducción: {error}")
                
            safe_delete(filename)
            
            fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error en play_next: {e}")

        vc.play(source, after=after_playing)

        global now_playing_message

        duration = data.get("duration", 0)
        
        embed = discord.Embed(
            title="🎵 Reproduciendo ahora",
            description=f"[{title}]({url})",
            color=discord.Color.green()
            )
        
        if "thumbnail" in data:
            embed.set_thumbnail(url=data["thumbnail"])
            
        if duration:
            embed.add_field(
                name="⏱️ Duración",
                value=f"{duration//60}:{duration%60:02}",
                inline=True
                )
            embed.add_field(
                name="⏱️ Progreso",
                value=progress_bar(0, duration),
                inline=False
                )
            embed.add_field(name="👤 Pedido por", value=ctx.author.mention, inline=True)
            embed.add_field(
                name="📜 Próximas canciones",
                value=format_queue(),
                inline=False
                )
        
        view = PlayerControls(vc)
        
        if now_playing_message:
            await now_playing_message.edit(embed=embed, view=view)
        else:
            now_playing_message = await ctx.send(embed=embed, view=view)
            bot.loop.create_task(update_progress_bar(vc, now_playing_message, duration))

    else:
        is_playing = False

@bot.command()
async def queue_list(ctx):
    if len(queue) == 0:
        await ctx.send("📭 Cola vacía")
        return

    embed = discord.Embed(
        title="📜 Cola de reproducción",
        color=discord.Color.blue()
    )

    for i, song in enumerate(queue[:10]):
        embed.add_field(
            name=f"{i+1}.",
            value=song["title"],
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def volume_cmd(ctx, vol: int):
    global volume

    if vol < 0 or vol > 100:
        await ctx.send("❌ Volumen entre 0 y 100")
        return

    volume = vol / 100

    vc = ctx.voice_client
    if vc and vc.source:
        vc.source.volume = volume

    await ctx.send(f"🔊 Volumen: {vol}%")

@bot.event
async def on_ready():
    cleanup_temp_files()
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
    
    loop = bot.loop
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    
    queue.append({
    "url": url,
    "title": data["title"]
})
    
    embed = discord.Embed(
        title="➕ Agregado a la cola",
        description=f"**{data['title']}**",
        color=discord.Color.orange()
        )
    
    await ctx.send(embed=embed)

    if not is_playing: 
        await play_next(ctx)
    else:
        if not ctx.voice_client.is_playing():
            await play_next(ctx)

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
async def leave(ctx):
    global is_playing

    vc = ctx.voice_client

    if vc:
        vc.stop()

        await asyncio.sleep(1)

        is_playing = False
        queue.clear()

        if hasattr(vc, "current_file"):
            safe_delete(vc.current_file)

        await vc.disconnect()

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
async def stop(ctx):
    global is_playing

    vc = ctx.voice_client

    if vc:
        vc.stop()

        is_playing = False
        queue.clear()

        if hasattr(vc, "current_file"):
            try:
                if os.path.exists(vc.current_file):
                    os.remove(vc.current_file)
                    print("Archivo borrado (stop)")
            except:
                pass

        await ctx.send("⏹️ Detenido y lista borrada")

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