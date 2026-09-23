# config.py
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BEWERBUNGS_CHANNEL_ID = int(os.getenv("BEWERBUNGS_CHANNEL_ID", "0"))
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")
PORT = int(os.getenv("PORT", "10000"))

# ---- Rollen (Namen exakt wie in Discord!) ----
ROLE_OWNER = "Owner 2"
ROLE_ADMIN = "Admin Rang"
ROLE_SUPPORT = "Support Rolle"

# ---- Zustand ----
BOT_AKTIV = True
MAINTENANCE_MODE = False
MAINTENANCE_REASON = "Keine Wartung"
BLOCKLIST = set()

# ---- Owner (max 4) ----
OWNERS = []          # Liste von Discord-IDs
MAX_OWNERS = 4

STATE_FILE = "bot_state.json"
OWNER_FILE = "owners.json"


# ------------------------------------------------------------
# STATE
# ------------------------------------------------------------
def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump({
            "BOT_AKTIV": BOT_AKTIV,
            "MAINTENANCE_MODE": MAINTENANCE_MODE,
            "MAINTENANCE_REASON": MAINTENANCE_REASON,
            "BLOCKLIST": list(BLOCKLIST)
        }, f)


def load_state():
    global BOT_AKTIV, MAINTENANCE_MODE, MAINTENANCE_REASON

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            d = json.load(f)
        BOT_AKTIV = d.get("BOT_AKTIV", True)
        MAINTENANCE_MODE = d.get("MAINTENANCE_MODE", False)
        MAINTENANCE_REASON = d.get("MAINTENANCE_REASON", "Keine Wartung")
        BLOCKLIST.update(d.get("BLOCKLIST", []))


# ------------------------------------------------------------
# OWNER
# ------------------------------------------------------------
def save_owners():
    with open(OWNER_FILE, "w") as f:
        json.dump({"OWNERS": OWNERS}, f)


def load_owners():
    global OWNERS
    if os.path.exists(OWNER_FILE):
        with open(OWNER_FILE) as f:
            OWNERS = json.load(f).get("OWNERS", [])


def is_owner(uid: int) -> bool:
    return uid in OWNERS


def add_owner(uid: int) -> bool:
    if uid in OWNERS:
        return False
    if len(OWNERS) >= MAX_OWNERS:
        return False
    OWNERS.append(uid)
    save_owners()
    return True


def remove_owner(uid: int) -> bool:
    if uid not in OWNERS:
        return False
    OWNERS.remove(uid)
    save_owners()
    return True