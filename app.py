import os
import time
import asyncio
import threading

import requests
import discord

from flask import Flask
from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BEWERBUNGS_CHANNEL_ID = int(os.getenv("BEWERBUNGS_CHANNEL_ID", "0"))

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")

WEBSITE_URL = os.getenv("WEBSITE_URL", "").strip()

PORT = int(os.getenv("PORT", "10000"))


# =========================================================
# FLASK WEBSITE
# =========================================================

app = Flask(__name__)

START_TIME = time.time()


@app.route("/")
def home():
    return "Discord Bot läuft! ✅", 200


@app.route("/health")
def health():
    return "OK", 200


def run_web():
    app.run(
        host="0.0.0.0",
        port=PORT
    )


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()

bot = discord.Client(
    intents=intents
)

tree = discord.app_commands.CommandTree(bot)


# =========================================================
# LISTEN
# =========================================================

blocklist_users = set()
whitelist_users = set()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def is_owner(interaction: discord.Interaction):
    return interaction.user.id == OWNER_ID


def is_admin(interaction: discord.Interaction):

    if interaction.user.id == OWNER_ID:
        return True

    if interaction.guild is None:
        return False

    member = interaction.guild.get_member(
        interaction.user.id
    )

    if member is None:
        return False

    return member.guild_permissions.administrator


async def require_admin(interaction: discord.Interaction):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ Du darfst diesen Befehl nicht benutzen.",
            ephemeral=True
        )

        return False

    return True


def format_uptime():

    seconds = int(
        time.time() - START_TIME
    )

    days, seconds = divmod(
        seconds,
        86400
    )

    hours, seconds = divmod(
        seconds,
        3600
    )

    minutes, seconds = divmod(
        seconds,
        60
    )

    result = []

    if days:
        result.append(
            f"{days}d"
        )

    if hours:
        result.append(
            f"{hours}h"
        )

    if minutes:
        result.append(
            f"{minutes}m"
        )

    result.append(
        f"{seconds}s"
    )

    return " ".join(result)


# =========================================================
# WEBSITE STATUS
# =========================================================

def check_website():

    if not WEBSITE_URL:

        return {
            "online": False,
            "status": None,
            "ping": None,
            "error": "WEBSITE_URL nicht gesetzt"
        }

    try:

        start = time.perf_counter()

        response = requests.get(
            WEBSITE_URL,
            timeout=10
        )

        ping = (
            time.perf_counter() - start
        ) * 1000

        return {
            "online": 200 <= response.status_code < 400,
            "status": response.status_code,
            "ping": ping,
            "error": None
        }

    except requests.RequestException as error:

        return {
            "online": False,
            "status": None,
            "ping": None,
            "error": str(error)
        }


# =========================================================
# BEWERBUNG MODAL
# =========================================================

class BewerbungModal(discord.ui.Modal):

    def __init__(
        self,
        rolle,
        erfahrung_vorlage,
        motivation_vorlage,
        staerken_vorlage
    ):

        super().__init__(
            title=f"Bewerbung – {rolle}"
        )

        self.rolle = rolle

        self.alter = discord.ui.TextInput(
            label="Wie alt bist du?",
            placeholder="z. B. 16",
            required=True,
            max_length=3
        )

        self.erfahrung = discord.ui.TextInput(
            label="Deine Erfahrung",
            placeholder=erfahrung_vorlage,
            default=erfahrung_vorlage,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.motivation = discord.ui.TextInput(
            label="Deine Motivation",
            placeholder=motivation_vorlage,
            default=motivation_vorlage,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        self.staerken = discord.ui.TextInput(
            label="Deine Stärken",
            placeholder=staerken_vorlage,
            default=staerken_vorlage,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(
            self.alter
        )

        self.add_item(
            self.erfahrung
        )

        self.add_item(
            self.motivation
        )

        self.add_item(
            self.staerken
        )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if BEWERBUNGS_CHANNEL_ID == 0:

            await interaction.response.send_message(
                "❌ Bewerbungs-Channel ist nicht konfiguriert.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            channel = await bot.fetch_channel(
                BEWERBUNGS_CHANNEL_ID
            )

        except discord.NotFound:

            await interaction.followup.send(
                "❌ Bewerbungs-Channel wurde nicht gefunden.",
                ephemeral=True
            )

            return

        except discord.Forbidden:

            await interaction.followup.send(
                "❌ Der Bot hat keine Berechtigung für den Bewerbungs-Channel.",
                ephemeral=True
            )

            return

        except discord.HTTPException as error:

            print(
                f"❌ Channel-Fehler: {error}"
            )

            await interaction.followup.send(
                "❌ Bewerbungs-Channel konnte nicht geladen werden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title=f"📋 Neue Bewerbung – {self.rolle}",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=(
                f"{interaction.user.mention}\n"
                f"ID: `{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.alter.value,
            inline=True
        )

        embed.add_field(
            name="💼 Rolle",
            value=self.rolle,
            inline=True
        )

        embed.add_field(
            name="💻 Erfahrung",
            value=self.erfahrung.value,
            inline=False
        )

        embed.add_field(
            name="💡 Motivation",
            value=self.motivation.value,
            inline=False
        )

        embed.add_field(
            name="⭐ Stärken",
            value=self.staerken.value,
            inline=False
        )

        embed.set_footer(
            text="Bewerbungssystem"
        )

        try:

            await channel.send(
                embed=embed
            )

            await interaction.followup.send(
                "✅ Deine Bewerbung wurde erfolgreich abgeschickt!",
                ephemeral=True
            )

        except discord.HTTPException as error:

            print(
                f"❌ Bewerbungsfehler: {error}"
            )

            await interaction.followup.send(
                "❌ Bewerbung konnte nicht gesendet werden.",
                ephemeral=True
            )


# =========================================================
# ROLLEN-SELECT
# =========================================================

class AutomatischesFormular(
    discord.ui.Select
):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Admin",
                description="Organisation, Verantwortung und Leitung",
                emoji="👑"
            ),

            discord.SelectOption(
                label="Moderator",
                description="Moderation, Regeln und Konfliktlösung",
                emoji="🛡️"
            ),

            discord.SelectOption(
                label="Supporter",
                description="Hilfe, Kommunikation und Support",
                emoji="💬"
            ),

            discord.SelectOption(
                label="Entwickler",
                description="Programmierung und Problemlösung",
                emoji="💻"
            )

        ]

        super().__init__(
            placeholder="Wähle deine gewünschte Rolle...",
            options=options,
            custom_id="bewerbung_rollen_select"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        rolle = self.values[0]

        vorlagen = {

            "Admin": {

                "erfahrung":
                    "Ich habe Erfahrung mit Organisation, Verantwortung oder Teamleitung.",

                "motivation":
                    "Ich möchte Verantwortung übernehmen und das Team unterstützen.",

                "staerken":
                    "Organisation, Verantwortungsbewusstsein und Teamarbeit."
            },

            "Moderator": {

                "erfahrung":
                    "Ich habe Erfahrung mit Moderation, Regelwerken oder Discord-Servern.",

                "motivation":
                    "Ich möchte dabei helfen, dass der Server freundlich, fair und ordentlich bleibt.",

                "staerken":
                    "Kommunikation, Geduld, Regelkenntnis und Konfliktlösung."
            },

            "Supporter": {

                "erfahrung":
                    "Ich habe Erfahrung darin, anderen bei Fragen oder Problemen zu helfen.",

                "motivation":
                    "Ich helfe gerne anderen Usern und möchte das Team im Support unterstützen.",

                "staerken":
                    "Hilfsbereitschaft, Geduld, Kommunikation und Zuverlässigkeit."
            },

            "Entwickler": {

                "erfahrung":
                    "Ich habe Erfahrung mit Programmierung und Entwicklung.",

                "motivation":
                    "Ich möchte bei technischen Projekten helfen und neue Funktionen entwickeln.",

                "staerken":
                    "Programmierung, logisches Denken, Problemlösung und Lernen."
            }

        }

        template = vorlagen[rolle]

        await interaction.response.send_modal(

            BewerbungModal(

                rolle=rolle,

                erfahrung_vorlage=template["erfahrung"],

                motivation_vorlage=template["motivation"],

                staerken_vorlage=template["staerken"]

            )
        )


# =========================================================
# BEWERBUNGS-VIEW
# =========================================================

class BewerbungView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        # WICHTIG:
        # Select wird direkt hinzugefügt.
        # Kein @discord.ui.select(...) !
        self.add_item(
            AutomatischesFormular()
        )

    @discord.ui.button(
        label="Supporter",
        emoji="💬",
        style=discord.ButtonStyle.primary,
        custom_id="bewerbung_supporter"
    )
    async def supporter(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(

            BewerbungModal(

                "Supporter",

                "Ich habe Erfahrung darin, anderen bei Fragen oder Problemen zu helfen.",

                "Ich helfe gerne anderen Usern und möchte das Team im Support unterstützen.",

                "Hilfsbereitschaft, Geduld, Kommunikation und Zuverlässigkeit."

            )
        )

    @discord.ui.button(
        label="Moderator",
        emoji="🛡️",
        style=discord.ButtonStyle.primary,
        custom_id="bewerbung_moderator"
    )
    async def moderator(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(

            BewerbungModal(

                "Moderator",

                "Ich habe Erfahrung mit Moderation, Regelwerken oder Discord-Servern.",

                "Ich möchte dabei helfen, dass der Server freundlich, fair und ordentlich bleibt.",

                "Kommunikation, Geduld, Regelkenntnis und Konfliktlösung."

            )
        )

    @discord.ui.button(
        label="Entwickler",
        emoji="💻",
        style=discord.ButtonStyle.success,
        custom_id="bewerbung_entwickler"
    )
    async def entwickler(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(

            BewerbungModal(

                "Entwickler",

                "Ich habe Erfahrung mit Programmierung und Entwicklung.",

                "Ich möchte bei technischen Projekten helfen und neue Funktionen entwickeln.",

                "Programmierung, logisches Denken, Problemlösung und Lernen."

            )
        )

    @discord.ui.button(
        label="Admin",
        emoji="👑",
        style=discord.ButtonStyle.danger,
        custom_id="bewerbung_admin"
    )
    async def admin(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(

            BewerbungModal(

                "Admin",

                "Ich habe Erfahrung mit Organisation, Verantwortung oder Teamleitung.",

                "Ich möchte Verantwortung übernehmen und das Team unterstützen.",

                "Organisation, Verantwortungsbewusstsein und Teamarbeit."

            )
        )


# =========================================================
# /BEWERBUNG
# =========================================================

@tree.command(
    name="bewerbung",
    description="Öffnet das Bewerbungsformular"
)
async def bewerbung(
    interaction: discord.Interaction
):

    if not await require_admin(
        interaction
    ):
        return

    embed = discord.Embed(
        title="📋 Team-Bewerbung",
        description=(
            "Du möchtest dem Team beitreten?\n\n"
            "Wähle unten deine gewünschte Position "
            "oder klicke direkt auf einen Button."
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
# /PING
# =========================================================

@tree.command(
    name="ping",
    description="Zeigt die aktuelle Discord-Latenz"
)
async def ping(
    interaction: discord.Interaction
):

    latency = bot.latency * 1000

    if latency < 100:
        status = "🟢 Sehr gut"

    elif latency < 250:
        status = "🟡 Normal"

    elif latency < 500:
        status = "🟠 Langsam"

    else:
        status = "🔴 Sehr langsam"

    await interaction.response.send_message(
        f"🏓 **Pong!**\n\n"
        f"📡 Discord Ping: `{latency:.0f} ms`\n"
        f"📊 Netzwerk: {status}",
        ephemeral=True
    )


# =========================================================
# BOT COMMAND GROUP
# =========================================================

bot_group = discord.app_commands.Group(
    name="bot",
    description="Bot-Verwaltung und Status"
)


# =========================================================
# /BOT STATUS
# =========================================================

@bot_group.command(
    name="status",
    description="Zeigt den Echtzeitstatus"
)
async def bot_status(
    interaction: discord.Interaction
):

    if not await require_admin(
        interaction
    ):
        return

    await interaction.response.defer(
        ephemeral=True
    )

    # Discord
    discord_ping = bot.latency * 1000

    if bot.is_ready():
        discord_status = "🟢 Online"
    else:
        discord_status = "🔴 Offline"

    # Website
    website = await asyncio.to_thread(
        check_website
    )

    if website["online"]:

        website_text = (
            f"🟢 Online\n"
            f"HTTP: `{website['status']}`\n"
            f"Ping: `{website['ping']:.0f} ms`"
        )

    elif website["status"] is not None:

        website_text = (
            f"🟠 Antwort erhalten\n"
            f"HTTP: `{website['status']}`\n"
            f"Ping: `{website['ping']:.0f} ms`"
        )

    else:

        website_text = (
            "🔴 Offline\n"
            f"`{website['error']}`"
        )

    # Netzwerk
    if discord_ping < 100:
        network = "🟢 Sehr gut"

    elif discord_ping < 250:
        network = "🟡 Normal"

    elif discord_ping < 500:
        network = "🟠 Langsam"

    else:
        network = "🔴 Sehr langsam"

    embed = discord.Embed(
        title="📡 Echtzeit-Systemstatus",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🤖 Discord Bot",
        value=(
            f"{discord_status}\n"
            f"WebSocket: `{discord_ping:.0f} ms`"
        ),
        inline=True
    )

    embed.add_field(
        name="🌐 Website",
        value=website_text,
        inline=True
    )

    embed.add_field(
        name="📡 Netzwerk",
        value=(
            f"{network}\n"
            f"Ping: `{discord_ping:.0f} ms`"
        ),
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=f"`{format_uptime()}`",
        inline=True
    )

    embed.add_field(
        name="🚫 Blocklist",
        value=f"`{len(blocklist_users)}` User",
        inline=True
    )

    embed.add_field(
        name="✅ Whitelist",
        value=f"`{len(whitelist_users)}` User",
        inline=True
    )

    embed.set_footer(
        text="Live-Systemstatus"
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# /BOT BLOCKLIST
# =========================================================

@bot_group.command(
    name="blocklist",
    description="Zeigt die Blocklist"
)
async def bot_blocklist(
    interaction: discord.Interaction
):

    if not await require_admin(
        interaction
    ):
        return

    if not blocklist_users:

        text = "Die Blocklist ist leer."

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
    description="Zeigt die Whitelist"
)
async def bot_whitelist(
    interaction: discord.Interaction
):

    if not await require_admin(
        interaction
    ):
        return

    if not whitelist_users:

        text = "Die Whitelist ist leer."

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
    description="Trennt den Bot von Discord"
)
async def bot_disconnect(
    interaction: discord.Interaction
):

    if not is_owner(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Nur der Owner darf diesen Befehl benutzen.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🔌 Bot wird von Discord getrennt...",
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
    description="Startet den Render-Service wirklich neu"
)
async def restart(
    interaction: discord.Interaction
):

    if not is_owner(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Du darfst diesen Befehl nicht benutzen.",
            ephemeral=True
        )

        return

    if not RENDER_API_KEY:

        await interaction.response.send_message(
            "❌ RENDER_API_KEY ist nicht konfiguriert.",
            ephemeral=True
        )

        return

    if not RENDER_SERVICE_ID:

        await interaction.response.send_message(
            "❌ RENDER_SERVICE_ID ist nicht konfiguriert.",
            ephemeral=True
        )

        return

    # Nachricht zuerst senden.
    # Danach wird Render neu gestartet.
    await interaction.response.send_message(
        "🔄 **Render-Neustart wird jetzt ausgelöst!**\n"
        "⏳ Der Bot startet gleich neu.",
        ephemeral=True
    )

    url = (
        "https://api.render.com/v1/services/"
        f"{RENDER_SERVICE_ID}/restart"
    )

    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json"
    }

    try:

        response = await asyncio.to_thread(
            requests.post,
            url,
            headers=headers,
            timeout=15
        )

        print(
            f"🔄 Render Restart Status: "
            f"{response.status_code}"
        )

        print(
            f"📄 Render Antwort: "
            f"{response.text}"
        )

        if response.status_code == 200:

            print(
                "✅ Render-Service wurde erfolgreich "
                "zum Neustart aufgefordert."
            )

        else:

            print(
                f"❌ Render API Fehler: "
                f"{response.status_code}"
            )

    except requests.RequestException as error:

        print(
            f"❌ Render API Fehler: {error}"
        )


# =========================================================
# BOT START
# =========================================================

@bot.event
async def on_ready():

    print("=" * 60)

    print(
        f"🤖 Eingeloggt als: {bot.user}"
    )

    print(
        f"🆔 Bot-ID: {bot.user.id}"
    )

    print(
        f"📡 Discord Ping: "
        f"{bot.latency * 1000:.0f} ms"
    )

    print(
        f"⏱️ Uptime: {format_uptime()}"
    )

    print("=" * 60)

    # Persistent View
    try:

        bot.add_view(
            BewerbungView()
        )

        print(
            "✅ Bewerbungs-View registriert."
        )

    except Exception as error:

        print(
            f"❌ Fehler bei Bewerbungs-View: {error}"
        )

    # Slash Commands synchronisieren
    try:

        synced = await tree.sync()

        print(
            f"✅ {len(synced)} Slash Commands synchronisiert."
        )

        for command in synced:

            print(
                f"   /{command.name}"
            )

    except Exception as error:

        print(
            f"❌ Slash-Command-Sync fehlgeschlagen: {error}"
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    if not TOKEN:

        raise RuntimeError(
            "❌ DISCORD_TOKEN fehlt!"
        )

    print(
        "🌐 Starte Flask-Webserver..."
    )

    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    print(
        "🤖 Starte Discord Bot..."
    )

    bot.run(
        TOKEN
    )
