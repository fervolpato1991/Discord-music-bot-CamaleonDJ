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

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class PlayerControls(discord.ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @discord.ui.button(label="⏯️", style=discord.ButtonStyle.green)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ Pausado", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ Reanudado", ephemeral=True)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.red)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.stop()
            await interaction.response.send_message("⏭️ Saltado", ephemeral=True)

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.grey)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc:
            self.vc.stop()
            await interaction.response.send_message("⏹️ Detenido", ephemeral=True)

def progress_bar(current, total, length=20):
    progress = int(length * current / total)
    bar = "▬" * progress + "🔘" + "▬" * (length - progress)
    return bar

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

        global now_playing_message

        duration = data.get("duration", 0)
        
        embed = discord.Embed(
            title="🎵 Reproduciendo ahora",
            description=f"[{title}]({url})",
            color=discord.Color.green()
            )
        
        if "thumbnail" in data:
            embed.set_thumbnail(url=data["thumbnail"])
            
        embed.add_field(name="⏱️ Progreso", value=progress_bar(0, duration), inline=False)
        
        view = PlayerControls(vc)
        
        if now_playing_message:
            await now_playing_message.edit(embed=embed, view=view)
        else:
            now_playing_message = await ctx.send(embed=embed, view=view)
        
        async def update_progress(vc, message, duration):
            current = 0
            
            while vc.is_playing() and current < duration:
                await asyncio.sleep(5)
                current += 5
                
                embed = message.embeds[0]
                embed.set_field_at(
                    0,
                    name="⏱️ Progreso",
                    value=progress_bar(current, duration),
                    inline=False
                )
                
                try:
                    await message.edit(embed=embed)
                except:
                    break

        bot.loop.create_task(update_progress(vc, now_playing_message, duration))

        if "thumbnail" in data:
            embed.set_thumbnail(url=data["thumbnail"])
            
        if "duration" in data:
            minutos = data["duration"] // 60
            segundos = data["duration"] % 60
            embed.add_field(name="Duración", value=f"{minutos}:{segundos:02}", inline=True)

            embed.add_field(name="Pedido por", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)

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
            try:
                if os.path.exists(vc.current_file):
                    os.remove(vc.current_file)
                    print("Archivo borrado (leave)")
            except:
                pass

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