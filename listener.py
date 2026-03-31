print("Listener iniciado")
import time
import requests
import psutil
import subprocess
from datetime import datetime 
import os

URL = "https://raw.githubusercontent.com/fervolpato1991/Discord-music-bot/refs/heads/main/start.txt"

LOG_PATH = os.path.join(os.path.dirname(__file__), "listener.log")

bot_running = False

def log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - {msg}\n")

def bot_ya_corriendo():
    for p in psutil.process_iter():
        try:
            if "bot.py" in " ".join(p.cmdline()):
                return True
        except:
            pass
    return False

while True:
    try:
        r = requests.get(URL)
        estado = r.text.strip()

        log(f"Estado leído: {estado}")

        if estado == "ON" and not bot_ya_corriendo():
            log("Encendiendo bot...")
            subprocess.Popen(["venv\\Scripts\\python.exe", "bot.py"])

    except Exception as e:
        log(f"Error: {e}")

    time.sleep(10)