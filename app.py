import os
import time
import asyncio
import threading

import requests
import discord

from flask import Flask
from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BEWERBUNGS_CHANNEL_ID = int(
    os.getenv("BEWERBUNGS_CHANNEL_ID", "0")
)

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")

WEBSITE_URL = os.getenv("WEBSITE_URL", "")
PORT = int(os.getenv("PORT", "10000"))


# =========================================================
# ENV CHECK
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN fehlt in den Environment Variables!"
    )

if OWNER_ID == 0:
    print("⚠️ OWNER_ID ist nicht gesetzt.")

if BEWERBUNGS_CHANNEL_ID == 0:
    print("⚠️ BEWERBUNGS_CHANNEL_ID ist nicht gesetzt.")


# =========================================================
# FLASK WEB SERVER
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Discord Bot läuft! ✅"


@app.route("/health")
def health():
    return "OK"


def run_web():
    print(f"🌐 Webserver startet auf Port {PORT}")

    app.run(
        host="0.0.0.0",
        port=PORT,
        use_reloader=False
    )


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()

bot = discord.Client(
    intents=intents
)

tree = discord.app_commands.CommandTree(bot)

START_TIME = time.time()

blocklist_users = set()
whitelist_users = set()

view_registered = False


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def get_uptime() -> str:
    seconds = int(
        time.time() - START_TIME
    )

    days = seconds // 86400
    seconds %= 86400

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    seconds %= 60

    return (
        f"{days}d "
        f"{hours}h "
        f"{minutes}m "
        f"{seconds}s"
    )


def website_online():

    if not WEBSITE_URL:
        return None

    try:

        response = requests.get(
            WEBSITE_URL,
            timeout=10
        )

        return response.status_code < 500

    except requests.RequestException:
        return False


# =========================================================
# BEWERBUNGS-VORLAGEN
# =========================================================

FORMULAR_VORLAGEN = {

    "Admin": {
        "beschreibung": "Bewerbung als Admin",

        "erfahrung": (
            "Welche Erfahrung hast du mit "
            "Discord-Servern oder Teamleitung?"
        ),

        "motivation": (
            "Warum möchtest du Admin werden "
            "und was würdest du am Server verbessern?"
        ),

        "zusatz": (
            "Welche Stärken bringst du als Admin mit?"
        )
    },

    "Moderator": {
        "beschreibung": "Bewerbung als Moderator",

        "erfahrung": (
            "Welche Erfahrung hast du mit "
            "Moderation oder Regelüberwachung?"
        ),

        "motivation": (
            "Warum möchtest du Moderator werden?"
        ),

        "zusatz": (
            "Was würdest du bei einem Streit "
            "zwischen zwei Usern machen?"
        )
    },

    "Supporter": {
        "beschreibung": "Bewerbung als Supporter",

        "erfahrung": (
            "Hast du bereits Erfahrung im Support "
            "oder im Umgang mit Usern?"
        ),

        "motivation": (
            "Warum möchtest du Supporter werden "
            "und wie würdest du einem User helfen?"
        ),

        "zusatz": (
            "Ein User ist unfreundlich. "
            "Wie würdest du reagieren?"
        )
    },

    "Entwickler": {
        "beschreibung": "Bewerbung als Entwickler",

        "erfahrung": (
            "Welche Programmiersprachen und "
            "Frameworks kannst du?"
        ),

        "motivation": (
            "Warum möchtest du Entwickler werden "
            "und was würdest du für den Server entwickeln?"
        ),

        "zusatz": (
            "Welche Projekte hast du bereits programmiert?"
        )
    }
}


# =========================================================
# BEWERBUNG MODAL
# =========================================================

class BewerbungModal(discord.ui.Modal):

    def __init__(self, rolle: str, auto_fill: bool = False):

        self.rolle = rolle
        self.auto_fill = auto_fill

        vorlage = FORMULAR_VORLAGEN.get(
            rolle,
            FORMULAR_VORLAGEN["Supporter"]
        )

        # Titel je nach Modus anpassen
        modus = "Auto" if auto_fill else "Manuell"
        super().__init__(
            title=f"{vorlage['beschreibung']} ({modus})"
        )

        # -------------------------------------------------
        # NAME (bei Auto-Fill vorausgefüllt)
        # -------------------------------------------------

        self.name = discord.ui.TextInput(
            label="Name",
            placeholder="Gib deinen Namen ein...",
            required=True,
            max_length=100,
            default=""  # Wird im on_submit oder über callback gesetzt
        )

        # -------------------------------------------------
        # ALTER (immer leer)
        # -------------------------------------------------

        self.alter = discord.ui.TextInput(
            label="Alter",
            placeholder="Wie alt bist du?",
            required=True,
            max_length=3
        )

        # -------------------------------------------------
        # ERFAHRUNG (immer leer)
        # -------------------------------------------------

        self.erfahrung = discord.ui.TextInput(
            label="Erfahrung",
            placeholder=vorlage["erfahrung"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        # -------------------------------------------------
        # MOTIVATION (immer leer)
        # -------------------------------------------------

        self.motivation = discord.ui.TextInput(
            label="Motivation",
            placeholder=vorlage["motivation"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        # -------------------------------------------------
        # ZUSATZFRAGE (immer leer)
        # -------------------------------------------------

        self.zusatz = discord.ui.TextInput(
            label="Zusatzfrage",
            placeholder=vorlage["zusatz"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        # -------------------------------------------------
        # FELDER HINZUFÜGEN
        # -------------------------------------------------

        self.add_item(self.name)
        self.add_item(self.alter)
        self.add_item(self.erfahrung)
        self.add_item(self.motivation)
        self.add_item(self.zusatz)

    # =====================================================
    # SUBMIT
    # =====================================================

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = bot.get_channel(
            BEWERBUNGS_CHANNEL_ID
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Der Bewerbungs-Channel wurde nicht gefunden.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # EMBED
        # -------------------------------------------------

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            description=(
                f"**Bewerbungsbereich:** {self.rolle}"
            ),
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Benutzer",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="📛 Name",
            value=self.name.value,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.alter.value,
            inline=True
        )

        embed.add_field(
            name="🎯 Bereich",
            value=self.rolle,
            inline=True
        )

        embed.add_field(
            name="📚 Erfahrung",
            value=self.erfahrung.value,
            inline=False
        )

        embed.add_field(
            name="💬 Motivation",
            value=self.motivation.value,
            inline=False
        )

        embed.add_field(
            name="📝 Zusatzfrage",
            value=self.zusatz.value,
            inline=False
        )

        embed.set_footer(
            text="Bewerbungssystem"
        )

        # -------------------------------------------------
        # SENDEN
        # -------------------------------------------------

        try:

            await channel.send(
                embed=embed
            )

            await interaction.response.send_message(
                "✅ Deine Bewerbung wurde erfolgreich abgeschickt!",
                ephemeral=True
            )

            print(
                f"📨 Neue Bewerbung: "
                f"{interaction.user} "
                f"→ {self.rolle}"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, "
                "im Bewerbungs-Channel zu schreiben.",
                ephemeral=True
            )

        except Exception as error:

            print(
                f"❌ Fehler beim Senden der Bewerbung: "
                f"{error}"
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "❌ Beim Absenden ist ein Fehler aufgetreten.",
                    ephemeral=True
                )


# =========================================================
# AUSWAHL: AUTO ODER MANUELL
# =========================================================

class ModusAuswahl(discord.ui.Select):

    def __init__(self, rolle: str):

        self.rolle = rolle

        options = [
            discord.SelectOption(
                label="🚀 Automatisch ausfüllen",
                value="auto",
                description="Name wird vorausgefüllt"
            ),
            discord.SelectOption(
                label="✏️ Manuell ausfüllen",
                value="manuell",
                description="Alle Felder selbst ausfüllen"
            )
        ]

        super().__init__(
            placeholder="📝 Wie möchtest du das Formular ausfüllen?",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        modus = self.values[0]
        auto_fill = (modus == "auto")

        # Modal erstellen
        modal = BewerbungModal(
            rolle=self.rolle,
            auto_fill=auto_fill
        )

        # Bei Auto-Fill den Namen des Users setzen
        if auto_fill:
            modal.name.default = str(interaction.user)

        await interaction.response.send_modal(modal)


# =========================================================
# VIEW FÜR MODUS-AUSWAHL
# =========================================================

class ModusView(discord.ui.View):

    def __init__(self, rolle: str):
        super().__init__(timeout=60)
        self.add_item(ModusAuswahl(rolle))


# =========================================================
# BEWERBUNG SELECT (Rollen-Auswahl)
# =========================================================

class AutomatischesFormular(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Admin",
                value="Admin",
                description="Bewerbung für das Admin-Team",
                emoji="👑"
            ),

            discord.SelectOption(
                label="Moderator",
                value="Moderator",
                description="Bewerbung für das Moderationsteam",
                emoji="🛡️"
            ),

            discord.SelectOption(
                label="Supporter",
                value="Supporter",
                description="Bewerbung für das Support-Team",
                emoji="💬"
            ),

            discord.SelectOption(
                label="Entwickler",
                value="Entwickler",
                description="Bewerbung als Entwickler",
                emoji="💻"
            )
        ]

        super().__init__(
            placeholder="📋 Wähle deine Bewerbung...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        rolle = self.values[0]

        # Statt direkt das Modal zu öffnen,
        # zeigen wir die Modus-Auswahl (Auto/Manuell)
        await interaction.response.send_message(
            "Möchtest du das Formular automatisch oder manuell ausfüllen?",
            view=ModusView(rolle),
            ephemeral=True
        )


# =========================================================
# BEWERBUNG VIEW
# =========================================================

class BewerbungView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            AutomatischesFormular()
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    global view_registered

    print("")
    print("===================================")
    print("🤖 BOT ONLINE")
    print(f"👤 Eingeloggt als: {bot.user}")
    print(f"🆔 Bot-ID: {bot.user.id}")
    print(
        f"📡 Ping: "
        f"{round(bot.latency * 1000)} ms"
    )
    print("===================================")
    print("")

    # -----------------------------------------------------
    # PERSISTENT VIEW
    # -----------------------------------------------------

    if not view_registered:

        bot.add_view(
            BewerbungView()
        )

        view_registered = True

        print(
            "✅ Bewerbung-View registriert."
        )

    # -----------------------------------------------------
    # SLASH COMMANDS
    # -----------------------------------------------------

    try:

        synced = await tree.sync()

        print(
            f"✅ {len(synced)} Slash Commands "
            f"synchronisiert."
        )

    except Exception as error:

        print(
            f"❌ Fehler beim Synchronisieren "
            f"der Commands: {error}"
        )


# =========================================================
# DISCONNECT
# =========================================================

@bot.event
async def on_disconnect():

    print(
        "⚠️ Discord-Verbindung getrennt."
    )

    print(
        "🔄 discord.py versucht automatisch, "
        "die Verbindung wiederherzustellen."
    )


# =========================================================
# RECONNECT
# =========================================================

@bot.event
async def on_resumed():

    print(
        "✅ Discord-Verbindung erfolgreich "
        "wiederhergestellt."
    )

    print(
        f"📡 Ping: "
        f"{round(bot.latency * 1000)} ms"
    )


# =========================================================
# WATCHDOG
# =========================================================

async def discord_watchdog():

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            if bot.is_ready():

                print(
                    "💚 Watchdog: Bot läuft | "
                    f"Ping: {round(bot.latency * 1000)} ms"
                )

            else:

                print(
                    "⚠️ Watchdog: "
                    "Bot ist momentan nicht bereit."
                )

        except Exception as error:

            print(
                f"⚠️ Watchdog-Fehler: {error}"
            )

        await asyncio.sleep(60)


# =========================================================
# SETUP HOOK
# =========================================================

async def setup_hook():

    asyncio.create_task(
        discord_watchdog()
    )


bot.setup_hook = setup_hook


# =========================================================
# /PING
# =========================================================

@tree.command(
    name="ping",
    description="Zeigt den Bot-Ping an."
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 Pong!\n"
        f"📡 Ping: **{latency} ms**"
    )


# =========================================================
# /BEWERBUNG
# =========================================================

@tree.command(
    name="bewerbung",
    description="Öffnet das Bewerbungsformular."
)
async def bewerbung(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="📋 Bewerbungen",
        description=(
            "Du möchtest Teil unseres Teams werden?\n\n"
            "Wähle unten den Bereich aus, "
            "für den du dich bewerben möchtest."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Bewerbungssystem"
    )

    await interaction.response.send_message(
        embed=embed,
        view=BewerbungView()
    )


# =========================================================
# BOT COMMAND GROUP
# =========================================================

bot_group = discord.app_commands.Group(
    name="bot",
    description="Bot-Verwaltung"
)


# =========================================================
# /BOT STATUS
# =========================================================

@bot_group.command(
    name="status",
    description="Zeigt den Bot-Status."
)
async def bot_status(
    interaction: discord.Interaction
):

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    latency = round(
        bot.latency * 1000
    )

    website = website_online()

    if website is None:

        website_status = (
            "⚪ Nicht konfiguriert"
        )

    elif website:

        website_status = "🟢 Online"

    else:

        website_status = "🔴 Offline"

    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Discord",
        value=(
            "🟢 Verbunden"
            if bot.is_ready()
            else "🔴 Getrennt"
        ),
        inline=False
    )

    embed.add_field(
        name="Ping",
        value=f"{latency} ms",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=get_uptime(),
        inline=True
    )

    embed.add_field(
        name="Website",
        value=website_status,
        inline=True
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# /BOT BLOCKLIST
# =========================================================

@bot_group.command(
    name="blocklist",
    description="Zeigt die Blocklist."
)
async def bot_blocklist(
    interaction: discord.Interaction
):

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    if not blocklist_users:

        text = (
            "Keine Benutzer auf der Blocklist."
        )

    else:

        text = "\n".join(
            f"• `{user_id}`"
            for user_id in blocklist_users
        )

    await interaction.response.send_message(
        f"🚫 **Blocklist**\n\n{text}",
        ephemeral=True
    )


# =========================================================
# /BOT WHITELIST
# =========================================================

@bot_group.command(
    name="whitelist",
    description="Zeigt die Whitelist."
)
async def bot_whitelist(
    interaction: discord.Interaction
):

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    if not whitelist_users:

        text = (
            "Keine Benutzer auf der Whitelist."
        )

    else:

        text = "\n".join(
            f"• `{user_id}`"
            for user_id in whitelist_users
        )

    await interaction.response.send_message(
        f"✅ **Whitelist**\n\n{text}",
        ephemeral=True
    )


# =========================================================
# /BOT DISCONNECT
# =========================================================

@bot_group.command(
    name="disconnect",
    description="Trennt den Bot manuell von Discord."
)
async def bot_disconnect(
    interaction: discord.Interaction
):

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🔌 Bot wird getrennt...",
        ephemeral=True
    )

    await bot.close()


# =========================================================
# BOT GROUP REGISTRIEREN
# =========================================================

tree.add_command(
    bot_group
)


# =========================================================
# /RESTART
# =========================================================

@tree.command(
    name="restart",
    description="Startet den Render-Service neu."
)
async def restart(
    interaction: discord.Interaction
):

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    if (
        not RENDER_API_KEY
        or not RENDER_SERVICE_ID
    ):

        await interaction.response.send_message(
            "❌ RENDER_API_KEY oder "
            "RENDER_SERVICE_ID fehlt.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🔄 Render-Service wird neu gestartet...",
        ephemeral=True
    )

    url = (
        "https://api.render.com/v1/services/"
        f"{RENDER_SERVICE_ID}/restart"
    )

    headers = {
        "Authorization": (
            f"Bearer {RENDER_API_KEY}"
        ),
        "Accept": "application/json"
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code in (
            200,
            201,
            202,
            204
        ):

            print(
                "✅ Render Restart "
                "erfolgreich ausgelöst."
            )

        else:

            print(
                "❌ Render Restart fehlgeschlagen: "
                f"{response.status_code} "
                f"{response.text}"
            )

    except requests.RequestException as error:

        print(
            f"❌ Fehler bei Render API: {error}"
        )


# =========================================================
# GLOBAL ERROR
# =========================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    print(
        f"❌ Discord Event Fehler: {event}"
    )


# =========================================================
# START
# =========================================================

def main():

    print("")
    print("===================================")
    print("🚀 Starte Discord Bot...")
    print("===================================")
    print("")

    # -----------------------------------------------------
    # FLASK STARTEN
    # -----------------------------------------------------

    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    # -----------------------------------------------------
    # DISCORD STARTEN
    # -----------------------------------------------------

    try:

        bot.run(TOKEN)

    except discord.LoginFailure:

        print(
            "❌ DISCORD_TOKEN ist ungültig."
        )

    except KeyboardInterrupt:

        print(
            "🛑 Bot manuell beendet."
        )

    except Exception as error:

        print(
            f"❌ Bot wurde beendet: {error}"
        )


# =========================================================
# PROGRAMM START
# =========================================================

if __name__ == "__main__":
    main()
