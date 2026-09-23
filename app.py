# app.py
import os
import sys
import time
import asyncio
import threading
import logging

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

import config


# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("bot")


# ---------- FLASK ----------
web = Flask(__name__)

@web.route("/")
def home():
    return "Bot läuft."

@web.route("/health")
def health():
    return {"status": "online", "bot_aktiv": config.BOT_AKTIV}

def run_web():
    web.run(host="0.0.0.0", port=config.PORT, use_reloader=False)


# ---------- BOT ----------
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

START = time.time()


def uptime():
    s = int(time.time() - START)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{d}d {h}h {m}m {s}s"


# ---------- BERECHTIGUNGEN ----------
def is_owner(uid: int) -> bool:
    """Prüft, ob die User-ID in der Owner-Liste steht."""
    return config.is_owner(uid)


def has_role_or_owner(interaction: discord.Interaction) -> bool:
    """Prüft: eingetragener Owner ODER Rolle Owner 2 / Admin Rang."""
    if config.is_owner(interaction.user.id):
        return True

    if isinstance(interaction.user, discord.Member):
        role_names = [r.name for r in interaction.user.roles]
        if config.ROLE_OWNER in role_names or config.ROLE_ADMIN in role_names:
            return True

    return False


# ---------- /ping ----------
@bot.tree.command(name="ping", description="Zeigt den Ping.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏓 Pong! **{round(bot.latency * 1000)} ms**"
    )


# ---------- /bot Gruppe ----------
bot_group = app_commands.Group(name="bot", description="Bot-Verwaltung")


@bot_group.command(name="an", description="Aktiviert den Bot.")
async def bot_an(interaction: discord.Interaction):
    if not has_role_or_owner(interaction):
        await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        return
    config.BOT_AKTIV = True
    config.save_state()
    await interaction.response.send_message("🟢 Bot aktiviert.", ephemeral=True)


@bot_group.command(name="aus", description="Deaktiviert den Bot.")
async def bot_aus(interaction: discord.Interaction):
    if not has_role_or_owner(interaction):
        await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        return
    config.BOT_AKTIV = False
    config.save_state()
    await interaction.response.send_message("🔴 Bot deaktiviert.", ephemeral=True)


@bot_group.command(name="status", description="Zeigt den Status.")
async def bot_status(interaction: discord.Interaction):
    if not has_role_or_owner(interaction):
        await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.green() if config.BOT_AKTIV else discord.Color.red()
    )
    embed.add_field(name="Bot", value="🟢 AN" if config.BOT_AKTIV else "🔴 AUS")
    embed.add_field(name="Wartung", value="🟠 AN" if config.MAINTENANCE_MODE else "🟢 AUS")
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)} ms")
    embed.add_field(name="Uptime", value=uptime(), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot_group.command(name="wartung", description="Wartungsmodus.")
@app_commands.describe(aktiv="Wartung an/aus", grund="Grund")
async def bot_wartung(interaction: discord.Interaction, aktiv: bool, grund: str = "Keine Angabe"):
    if not has_role_or_owner(interaction):
        await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        return
    config.MAINTENANCE_MODE = aktiv
    config.MAINTENANCE_REASON = grund if aktiv else "Keine Wartung"
    config.save_state()
    await interaction.response.send_message(
        f"🛠️ Wartung: {'AN' if aktiv else 'AUS'} | Grund: {grund}",
        ephemeral=True
    )


@bot_group.command(name="block", description="User blockieren.")
async def bot_block(interaction: discord.Interaction, user_id: str):
    if not has_role_or_owner(interaction):
        await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        return
    try:
        uid = int(user_id)
    except ValueError:
        await interaction.response.send_message("❌ Ungültige ID.", ephemeral=True)
        return
    config.BLOCKLIST.add(uid)
    config.save_state()
    await interaction.response.send_message(f"🚫 `{uid}` blockiert.", ephemeral=True)


bot.tree.add_command(bot_group)


# ---------- /restart ----------
@bot.tree.command(name="restart", description="Startet den Bot neu.")
async def restart(interaction: discord.Interaction):
    if not has_role_or_owner(interaction):
        await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
        return
    await interaction.response.send_message("🔄 Neustart in 3 Sekunden...", ephemeral=True)
    await asyncio.sleep(3)
    os.execv(sys.executable, [sys.executable, sys.argv[0]])


# ---------- /splash ----------
@bot.tree.command(name="splash", description="Sendet das Splash-Bild.")
async def splash(interaction: discord.Interaction):
    if os.path.exists("splash.png"):
        await interaction.response.send_message(file=discord.File("splash.png"))
    else:
        await interaction.response.send_message("❌ splash.png nicht gefunden.", ephemeral=True)


# ---------- READY ----------
@bot.event
async def on_ready():
    log.info(f"✅ Eingeloggt als {bot.user}")

    # Cogs laden
    for ext in ("app1", "owner_check"):
        try:
            await bot.load_extension(ext)
            log.info(f"✅ {ext}.py geladen")
        except Exception as e:
            log.exception(f"❌ {ext}.py konnte nicht geladen werden: {e}")

    # Sync
    try:
        if config.TEST_GUILD_ID:
            guild = discord.Object(id=int(config.TEST_GUILD_ID))

            # Commands in die Test-Guild kopieren
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)

            log.info(f"✅ {len(synced)} Commands in Test-Guild synchronisiert")
        else:
            synced = await bot.tree.sync()
            log.info(f"✅ {len(synced)} Commands global synchronisiert")
    except Exception as e:
        log.exception(f"❌ Sync-Fehler: {e}")


# ---------- WATCHDOG ----------
async def watchdog():
    await bot.wait_until_ready()
    while not bot.is_closed():
        log.info(f"💚 Watchdog | Ping {round(bot.latency * 1000)} ms")
        await asyncio.sleep(60)


# ---------- MAIN ----------
def main():
    config.load_state()
    config.load_owners()          # ✅ Owner laden

    threading.Thread(target=run_web, daemon=True).start()
    log.info(f"🌐 Flask auf Port {config.PORT}")

    async def hook():
        asyncio.create_task(watchdog())

    bot.setup_hook = hook

    bot.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()