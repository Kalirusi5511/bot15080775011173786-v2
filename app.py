import os
import sys
import time
import asyncio
import threading
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv


# ============================================================
# ENV
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

BEWERBUNGS_CHANNEL_ID = int(
    os.getenv("BEWERBUNGS_CHANNEL_ID", "0")
)

ANNOUNCEMENT_CHANNEL_ID = int(
    os.getenv("ANNOUNCEMENT_CHANNEL_ID", "0")
)

WEBSITE_URL = os.getenv(
    "WEBSITE_URL",
    "https://example.com"
)

PORT = int(os.getenv("PORT", "10000"))

TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN fehlt in der .env-Datei."
    )


# ============================================================
# LOGGING
# ============================================================

LOG_FILE = "bot.log"

LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(message)s"
)

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=2_000_000,
    backupCount=3,
    encoding="utf-8"
)

file_handler.setFormatter(
    logging.Formatter(LOG_FORMAT)
)


console_handler = logging.StreamHandler()

console_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
)


logger = logging.getLogger("discord_bot")

logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ------------------------------------------------------------
# Ping-Logger
#
# Dieser Logger schreibt NUR in bot.log.
# Dadurch wird der Ping nicht jede Minute in der
# Konsole gespammt.
# ------------------------------------------------------------

ping_logger = logging.getLogger("discord_bot_ping")

ping_logger.setLevel(logging.INFO)
ping_logger.handlers.clear()
ping_logger.propagate = False

ping_file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=2_000_000,
    backupCount=3,
    encoding="utf-8"
)

ping_file_handler.setFormatter(
    logging.Formatter(LOG_FORMAT)
)

ping_logger.addHandler(ping_file_handler)


# ============================================================
# STATUS
# ============================================================

START_TIME = time.time()

BOT_AKTIV = True

MAINTENANCE_MODE = False
MAINTENANCE_REASON = "Keine Wartung"

blocklist_users = set()
whitelist_users = set()


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Discord Bot läuft."


@app.route("/health")
def health():
    return {
        "status": "online",
        "bot_aktiv": BOT_AKTIV,
        "wartung": MAINTENANCE_MODE
    }


def run_flask():
    logger.info(
        f"🌐 Flask startet auf Port {PORT}"
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        use_reloader=False
    )


# ============================================================
# DISCORD CLIENT
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.members = True


class MyBot(discord.Client):

    def __init__(self):
        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )

        self.application_view_added = False


bot = MyBot()


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def uptime_text() -> str:
    seconds = int(time.time() - START_TIME)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return (
        f"{days}d "
        f"{hours}h "
        f"{minutes}m "
        f"{seconds}s"
    )


async def safe_response(
    interaction: discord.Interaction,
    *,
    content=None,
    embed=None,
    view=None,
    ephemeral=False
):

    kwargs = {
        "content": content,
        "embed": embed,
        "ephemeral": ephemeral
    }

    # WICHTIG:
    # view=None darf nicht an discord.py übergeben werden.
    if view is not None:
        kwargs["view"] = view

    try:

        if interaction.response.is_done():

            return await interaction.followup.send(
                **kwargs
            )

        return await interaction.response.send_message(
            **kwargs
        )

    except discord.HTTPException as error:

        logger.error(
            f"❌ Discord Response Fehler: {error}"
        )

        return None


# ============================================================
# APPLICATION SYSTEM
# ============================================================

class BewerbungModal(discord.ui.Modal):

    def __init__(self):

        super().__init__(
            title="Bewerbung"
        )

        self.name_field = discord.ui.TextInput(
            label="Name",
            placeholder="Dein Name",
            required=True,
            max_length=100
        )

        self.age_field = discord.ui.TextInput(
            label="Alter",
            placeholder="Dein Alter",
            required=True,
            max_length=3
        )

        self.experience_field = discord.ui.TextInput(
            label="Erfahrung",
            placeholder="Erzähle etwas über deine Erfahrung.",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.motivation_field = discord.ui.TextInput(
            label="Motivation",
            placeholder="Warum möchtest du dich bewerben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.name_field)
        self.add_item(self.age_field)
        self.add_item(self.experience_field)
        self.add_item(self.motivation_field)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="📩 Neue Bewerbung",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="👤 Name",
            value=self.name_field.value,
            inline=False
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age_field.value,
            inline=False
        )

        embed.add_field(
            name="💼 Erfahrung",
            value=self.experience_field.value,
            inline=False
        )

        embed.add_field(
            name="💡 Motivation",
            value=self.motivation_field.value,
            inline=False
        )

        embed.set_footer(
            text=f"Discord ID: {interaction.user.id}"
        )

        channel = bot.get_channel(
            BEWERBUNGS_CHANNEL_ID
        )

        if channel is None:

            await safe_response(
                interaction,
                content=(
                    "❌ Der Bewerbungs-Channel "
                    "wurde nicht gefunden."
                ),
                ephemeral=True
            )

            logger.error(
                "❌ Bewerbungs-Channel nicht gefunden."
            )

            return

        try:

            await channel.send(
                embed=embed
            )

            await safe_response(
                interaction,
                content=(
                    "✅ Deine Bewerbung wurde "
                    "erfolgreich abgeschickt."
                ),
                ephemeral=True
            )

            logger.info(
                f"📩 Bewerbung von "
                f"{interaction.user} "
                f"({interaction.user.id})"
            )

        except discord.HTTPException as error:

            await safe_response(
                interaction,
                content=(
                    "❌ Die Bewerbung konnte "
                    "nicht gesendet werden."
                ),
                ephemeral=True
            )

            logger.error(
                f"❌ Bewerbungsfehler: {error}"
            )


class BewerbungView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Bewerben",
        style=discord.ButtonStyle.green,
        emoji="📩",
        custom_id="bewerbung_button"
    )
    async def bewerben_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not BOT_AKTIV:

            await safe_response(
                interaction,
                content=(
                    "🔴 Der Bot ist momentan deaktiviert."
                ),
                ephemeral=True
            )

            return

        if MAINTENANCE_MODE:

            await safe_response(
                interaction,
                content=(
                    "🛠️ Der Bot befindet sich "
                    "momentan im Wartungsmodus."
                ),
                ephemeral=True
            )

            return

        if interaction.user.id in blocklist_users:

            await safe_response(
                interaction,
                content=(
                    "❌ Du bist für Bewerbungen gesperrt."
                ),
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            BewerbungModal()
        )


# ============================================================
# PING
# ============================================================

@bot.tree.command(
    name="ping",
    description="Zeigt den aktuellen Bot-Ping."
)
async def ping(
    interaction: discord.Interaction
):

    ping_ms = round(
        bot.latency * 1000
    )

    await safe_response(
        interaction,
        content=(
            f"🏓 **Pong!**\n"
            f"📡 Ping: **{ping_ms} ms**"
        )
    )

    logger.info(
        f"🏓 /ping von {interaction.user} "
        f"| {ping_ms} ms"
    )


# ============================================================
# BEWERBUNG
# ============================================================

@bot.tree.command(
    name="bewerbung",
    description="Öffnet das Bewerbungsformular."
)
async def bewerbung(
    interaction: discord.Interaction
):

    if not BOT_AKTIV:

        await safe_response(
            interaction,
            content="🔴 Der Bot ist deaktiviert.",
            ephemeral=True
        )

        return

    if MAINTENANCE_MODE:

        await safe_response(
            interaction,
            content=(
                "🛠️ Der Bot befindet sich "
                "im Wartungsmodus."
            ),
            ephemeral=True
        )

        return

    if interaction.user.id in blocklist_users:

        await safe_response(
            interaction,
            content=(
                "❌ Du bist für Bewerbungen gesperrt."
            ),
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="📩 Bewerbung",
        description=(
            "Klicke auf den Button unten, "
            "um eine Bewerbung zu starten."
        ),
        color=discord.Color.green()
    )

    await safe_response(
        interaction,
        embed=embed,
        view=BewerbungView()
    )


# ============================================================
# BOT GROUP
# ============================================================

bot_group = app_commands.Group(
    name="bot",
    description="Bot-Verwaltung"
)


# ------------------------------------------------------------
# /bot an
# ------------------------------------------------------------

@bot_group.command(
    name="an",
    description="Aktiviert den Bot."
)
async def bot_an(
    interaction: discord.Interaction
):

    global BOT_AKTIV

    if not is_owner(interaction.user.id):

        await safe_response(
            interaction,
            content="❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    BOT_AKTIV = True

    await safe_response(
        interaction,
        content="🟢 Bot wurde aktiviert.",
        ephemeral=True
    )

    logger.info(
        f"🟢 Bot aktiviert von "
        f"{interaction.user}"
    )


# ------------------------------------------------------------
# /bot aus
# ------------------------------------------------------------

@bot_group.command(
    name="aus",
    description="Deaktiviert den Bot."
)
async def bot_aus(
    interaction: discord.Interaction
):

    global BOT_AKTIV

    if not is_owner(interaction.user.id):

        await safe_response(
            interaction,
            content="❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    BOT_AKTIV = False

    await safe_response(
        interaction,
        content="🔴 Bot wurde deaktiviert.",
        ephemeral=True
    )

    logger.info(
        f"🔴 Bot deaktiviert von "
        f"{interaction.user}"
    )


# ------------------------------------------------------------
# /bot status
# ------------------------------------------------------------

@bot_group.command(
    name="status",
    description="Zeigt den aktuellen Bot-Status."
)
async def bot_status(
    interaction: discord.Interaction
):

    ping_ms = round(
        bot.latency * 1000
    )

    bot_status_text = (
        "🟢 AN"
        if BOT_AKTIV
        else "🔴 AUS"
    )

    maintenance_text = (
        "🟠 AN"
        if MAINTENANCE_MODE
        else "🟢 AUS"
    )

    embed = discord.Embed(
        title="🤖 Bot Status",
        color=(
            discord.Color.green()
            if BOT_AKTIV
            else discord.Color.red()
        )
    )

    embed.add_field(
        name="Bot",
        value=bot_status_text,
        inline=True
    )

    embed.add_field(
        name="Wartung",
        value=maintenance_text,
        inline=True
    )

    embed.add_field(
        name="Ping",
        value=f"{ping_ms} ms",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=uptime_text(),
        inline=False
    )

    await safe_response(
        interaction,
        embed=embed,
        ephemeral=True
    )


# ------------------------------------------------------------
# /bot wartung
# ------------------------------------------------------------

@bot_group.command(
    name="wartung",
    description="Schaltet den Wartungsmodus."
)
@app_commands.describe(
    aktiv="Wartung an oder aus",
    grund="Optionaler Wartungsgrund"
)
async def bot_wartung(
    interaction: discord.Interaction,
    aktiv: bool,
    grund: str = "Keine Angabe"
):

    global MAINTENANCE_MODE
    global MAINTENANCE_REASON

    if not is_owner(interaction.user.id):

        await safe_response(
            interaction,
            content="❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    MAINTENANCE_MODE = aktiv

    if aktiv:
        MAINTENANCE_REASON = grund

    if aktiv:

        message = (
            "🛠️ Wartungsmodus **aktiviert**.\n"
            f"Grund: **{grund}**"
        )

    else:

        message = (
            "🟢 Wartungsmodus **deaktiviert**."
        )

    await safe_response(
        interaction,
        content=message,
        ephemeral=True
    )

    logger.info(
        f"🛠️ Wartungsmodus: "
        f"{'AN' if aktiv else 'AUS'} "
        f"| Grund: {grund}"
    )


# ------------------------------------------------------------
# /bot blocklist
# ------------------------------------------------------------

@bot_group.command(
    name="blocklist",
    description="Fügt einen User zur Blocklist hinzu."
)
@app_commands.describe(
    user_id="Discord User ID"
)
async def bot_blocklist(
    interaction: discord.Interaction,
    user_id: str
):

    if not is_owner(interaction.user.id):

        await safe_response(
            interaction,
            content="❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    try:

        target_id = int(user_id)

    except ValueError:

        await safe_response(
            interaction,
            content="❌ Ungültige User-ID.",
            ephemeral=True
        )

        return

    blocklist_users.add(target_id)

    await safe_response(
        interaction,
        content=(
            f"🚫 `{target_id}` wurde "
            "zur Blocklist hinzugefügt."
        ),
        ephemeral=True
    )

    logger.info(
        f"🚫 Blocklist + {target_id}"
    )


# ------------------------------------------------------------
# /bot whitelist
# ------------------------------------------------------------

@bot_group.command(
    name="whitelist",
    description="Fügt einen User zur Whitelist hinzu."
)
@app_commands.describe(
    user_id="Discord User ID"
)
async def bot_whitelist(
    interaction: discord.Interaction,
    user_id: str
):

    if not is_owner(interaction.user.id):

        await safe_response(
            interaction,
            content="❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    try:

        target_id = int(user_id)

    except ValueError:

        await safe_response(
            interaction,
            content="❌ Ungültige User-ID.",
            ephemeral=True
        )

        return

    whitelist_users.add(target_id)

    await safe_response(
        interaction,
        content=(
            f"✅ `{target_id}` wurde "
            "zur Whitelist hinzugefügt."
        ),
        ephemeral=True
    )

    logger.info(
        f"✅ Whitelist + {target_id}"
    )


# ------------------------------------------------------------
# /bot disconnect
# ------------------------------------------------------------

@bot_group.command(
    name="disconnect",
    description="Trennt den Bot von Discord."
)
async def bot_disconnect(
    interaction: discord.Interaction
):

    if not is_owner(interaction.user.id):

        await safe_response(
            interaction,
            content="❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    await safe_response(
        interaction,
        content=(
            "🔌 Bot wird jetzt von Discord getrennt."
        ),
        ephemeral=True
    )

    logger.warning(
        f"🔌 Bot Disconnect von "
        f"{interaction.user}"
    )

    await asyncio.sleep(1)

    await bot.close()


bot.tree.add_command(bot_group)


# ============================================================
# LOKALER RESTART
# ============================================================

def restart_local_app():

    logger.warning(
        "🔄 Lokaler Neustart wird ausgeführt..."
    )

    python = sys.executable

    script = os.path.abspath(
        sys.argv[0]
    )

    logger.info(
        f"🐍 Python: {python}"
    )

    logger.info(
        f"📄 Script: {script}"
    )

    # Wichtig:
    # Der aktuelle Prozess wird ersetzt.
    # Dadurch entsteht KEIN zweiter Discord-Client.
    os.execv(
        python,
        [
            python,
            script,
            *sys.argv[1:]
        ]
    )


@bot.tree.command(
    name="restart",
    description="Startet die lokale app.py neu."
)
async def restart(
    interaction: discord.Interaction
):

    if not is_owner(interaction.user.id):

        await safe_response(
            interaction,
            content="❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    logger.warning(
        f"🔄 Restart angefordert von "
        f"{interaction.user}"
    )

    await safe_response(
        interaction,
        content=(
            "🔄 **Lokaler Neustart wird ausgeführt...**\n\n"
            "⏱️ Neustart in **5 Sekunden**..."
        ),
        ephemeral=True
    )

    try:

        message = await interaction.original_response()

    except discord.HTTPException as error:

        logger.error(
            f"❌ Restart-Nachricht konnte "
            f"nicht geladen werden: {error}"
        )

        await asyncio.sleep(5)

        restart_local_app()

        return

    for seconds in range(4, 0, -1):

        await asyncio.sleep(1)

        try:

            await message.edit(
                content=(
                    "🔄 **Lokaler Neustart wird ausgeführt...**\n\n"
                    f"⏱️ Neustart in **{seconds} "
                    f"{'Sekunde' if seconds == 1 else 'Sekunden'}**..."
                )
            )

        except discord.NotFound:

            logger.warning(
                "⚠️ Restart-Nachricht wurde gelöscht."
            )

        except discord.HTTPException as error:

            logger.warning(
                f"⚠️ Restart-Nachricht konnte "
                f"nicht bearbeitet werden: {error}"
            )

    try:

        await message.edit(
            content=(
                "🔄 **Lokaler Neustart wird ausgeführt...**\n\n"
                "✅ **Neustart jetzt!**\n"
                "⏳ `app.py` wird neu gestartet..."
            )
        )

    except discord.HTTPException as error:

        logger.warning(
            f"⚠️ Letzte Restart-Nachricht "
            f"konnte nicht bearbeitet werden: {error}"
        )

    await asyncio.sleep(0.5)

    restart_local_app()


# ============================================================
# WATCHDOG
# ============================================================

async def discord_watchdog():

    await bot.wait_until_ready()

    logger.info(
        "💚 Watchdog gestartet."
    )

    while not bot.is_closed():

        try:

            if bot.is_ready():

                ping_ms = round(
                    bot.latency * 1000
                )

                bot_status = (
                    "AN"
                    if BOT_AKTIV
                    else "AUS"
                )

                maintenance_status = (
                    "AN"
                    if MAINTENANCE_MODE
                    else "AUS"
                )

                # NUR in bot.log.
                # NICHT in die Konsole.
                ping_logger.info(
                    "💚 Watchdog | "
                    f"Ping: {ping_ms} ms | "
                    f"Bot: {bot_status} | "
                    f"Wartung: {maintenance_status}"
                )

        except Exception as error:

            logger.error(
                f"❌ Watchdog-Fehler: {error}"
            )

        # Alle 60 Sekunden genau EIN Log-Eintrag.
        await asyncio.sleep(60)


# ============================================================
# DISCORD EVENTS
# ============================================================

@bot.event
async def on_ready():

    global BOT_AKTIV

    BOT_AKTIV = True

    logger.info(
        f"✅ Eingeloggt als "
        f"{bot.user} "
        f"(ID: {bot.user.id})"
    )

    logger.info(
        f"📡 Aktueller Ping: "
        f"{round(bot.latency * 1000)} ms"
    )

    # Persistent View nur einmal hinzufügen.
    if not bot.application_view_added:

        bot.add_view(
            BewerbungView()
        )

        bot.application_view_added = True

        logger.info(
            "📩 Bewerbungs-View registriert."
        )

    # --------------------------------------------------------
    # Commands synchronisieren
    # --------------------------------------------------------

    try:

        if TEST_GUILD_ID:

            guild_id = int(
                TEST_GUILD_ID
            )

            guild = discord.Object(
                id=guild_id
            )

            bot.tree.copy_global_to(
                guild=guild
            )

            synced = await bot.tree.sync(
                guild=guild
            )

            logger.info(
                f"🔧 {len(synced)} Commands "
                f"mit Test-Guild synchronisiert."
            )

        else:

            synced = await bot.tree.sync()

            logger.info(
                f"🔧 {len(synced)} globale "
                f"Commands synchronisiert."
            )

    except Exception as error:

        logger.exception(
            f"❌ Command-Sync fehlgeschlagen: "
            f"{error}"
        )


@bot.event
async def on_disconnect():

    logger.warning(
        "🔌 Discord-Verbindung getrennt."
    )


@bot.event
async def on_resumed():

    logger.info(
        "🔄 Discord-Verbindung wiederhergestellt."
    )


@bot.event
async def on_error(
    event_method,
    *args,
    **kwargs
):

    logger.exception(
        f"❌ Fehler in Event: "
        f"{event_method}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "========================================"
    )

    logger.info(
        "🚀 app.py wird gestartet..."
    )

    logger.info(
        f"🐍 Python: {sys.version.split()[0]}"
    )

    logger.info(
        f"📄 Log-Datei: {os.path.abspath(LOG_FILE)}"
    )

    logger.info(
        "========================================"
    )

    flask_thread = threading.Thread(
        target=run_flask,
        daemon=True
    )

    flask_thread.start()

    logger.info(
        "🌐 Flask-Server gestartet."
    )

    logger.info(
        "🤖 Discord Client startet..."
    )

    bot.run(
        TOKEN,
        log_handler=None
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        logger.warning(
            "🛑 Bot manuell beendet."
        )

    except Exception as error:

        logger.exception(
            f"💥 Kritischer Fehler: {error}"
        )
