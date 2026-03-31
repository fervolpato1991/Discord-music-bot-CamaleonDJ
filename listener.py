import time
import requests
import psutil
import subprocess
from datetime import datetime 
import os

STATE_FILE = "start.txt"

LOG_PATH = os.path.join(os.path.dirname(__file__), "listener.log")

BOT_ACTIVO = False

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

ultimo_estado = None

while True:
    try:
        with open(STATE_FILE, "r") as f:
            estado = f.read().strip()

        if estado != ultimo_estado:
            log(f"Estado cambiado: {estado}")
            ultimo_estado = estado

        if estado == "ON" and not BOT_ACTIVO:
            log("Encendiendo bot...")
            subprocess.Popen(["venv\\Scripts\\python.exe", "bot.py"])
            BOT_ACTIVO = True
            time.sleep(30)
        
        if estado == "OFF":
            BOT_ACTIVO = False

    except Exception as e:
        log(f"Error: {e}")

    time.sleep(10)