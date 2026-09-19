# config.py
import os

# --- Token & IDs aus Umgebungsvariablen ---
TOKEN = os.getenv("DISCORD_TOKEN", "DEIN_TOKEN_FALLBACK_HIER")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
SUPPORTER_ROLE = os.getenv("SUPPORTER_ROLE", "Supporter")

# --- Dateien ---
CSV_FILE = "formulare.csv"
SPLASH_IMAGE = "splash.png"

# --- Render / Web Service ---
PORT = int(os.getenv("PORT", "8080"))
