import os
import time
import asyncio
import threading

import requests
import discord

from flask import Flask
from dotenv import load_dotenv


# =========================================================
# ENV
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BEWERBUNGS_CHANNEL_ID = int(os.getenv("BEWERBUNGS_CHANNEL_ID", "0"))

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")

# Öffentliche Website des Render-Services
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
# TEMPORÄRE LISTEN
# =========================================================

blocklist = set()
whitelist = set()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def format_uptime():
    seconds = int(time.time() - START_TIME)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    return " ".join(parts)


def is_owner(interaction: discord.Interaction):
    return interaction.user.id == OWNER_ID


def is_admin(interaction: discord.Interaction):
    if interaction.user.id == OWNER_ID:
        return True

    if interaction.guild is None:
        return False

    member = interaction.guild.get_member(interaction.user.id)

    if member is None:
        return False

    return member.guild_permissions.administrator


async def check_admin(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Du darfst diesen Befehl nicht benutzen.",
            ephemeral=True
        )
        return False

    return True


# =========================================================
# BEWERBUNG MODAL
# =========================================================

class BewerbungModal(discord.ui.Modal):
    def __init__(
        self,
        rolle: str,
        motivation_vorlage: str,
        staerken_vorlage: str,
        erfahrung_vorlage: str
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
            label="Erfahrung",
            placeholder=erfahrung_vorlage,
            default=erfahrung_vorlage,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.motivation = discord.ui.TextInput(
            label="Warum möchtest du beitreten?",
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

        self.add_item(self.alter)
        self.add_item(self.erfahrung)
        self.add_item(self.motivation)
        self.add_item(self.staerken)

    async def on_submit(self, interaction: discord.Interaction):

        if BEWERBUNGS_CHANNEL_ID == 0:
            await interaction.response.send_message(
                "❌ Der Bewerbungs-Channel ist nicht konfiguriert.",
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
                "❌ Der Bewerbungs-Channel wurde nicht gefunden.",
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
            print(f"❌ Fehler beim Laden des Bewerbungs-Channels: {error}")

            await interaction.followup.send(
                "❌ Der Bewerbungs-Channel konnte nicht geladen werden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📋 Neue Bewerbung – {self.rolle}",
            description=(
                f"**Bewerber:** {interaction.user.mention}\n"
                f"**User-ID:** `{interaction.user.id}`"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.alter.value,
            inline=True
        )

        embed.add_field(
            name="👤 Rolle",
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
            print(f"❌ Fehler beim Senden der Bewerbung: {error}")

            await interaction.followup.send(
                "❌ Die Bewerbung konnte nicht gesendet werden.",
                ephemeral=True
            )


# =========================================================
# BEWERBUNGS-DROPDOWN
# =========================================================

class AutomatischesFormular(discord.ui.Select):

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
                description="Hilfe, Kommunikation und Geduld",
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
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        vorlagen = {

            "Admin": {
                "erfahrung": "Ich habe Erfahrung mit Organisation, Verantwortung oder Teamleitung.",
                "motivation": "Ich möchte Verantwortung übernehmen und das Team bei der Organisation unterstützen.",
                "staerken": "Organisation, Verantwortungsbewusstsein und Teamarbeit."
            },

            "Moderator": {
                "erfahrung": "Ich habe Erfahrung mit Moderation, Regelwerken oder Discord-Servern.",
                "motivation": "Ich möchte dabei helfen, dass der Server freundlich, fair und ordentlich bleibt.",
                "staerken": "Kommunikation, Geduld, Regelkenntnis und Konfliktlösung."
            },

            "Supporter": {
                "erfahrung": "Ich habe Erfahrung darin, anderen bei Fragen oder Problemen zu helfen.",
                "motivation": "Ich helfe gerne anderen Usern und möchte das Team im Support unterstützen.",
                "staerken": "Hilfsbereitschaft, Geduld, Kommunikation und Zuverlässigkeit."
            },

            "Entwickler": {
                "erfahrung": "Ich habe Erfahrung mit Programmierung und Entwicklung.",
                "motivation": "Ich möchte bei technischen Projekten helfen und neue Funktionen entwickeln.",
                "staerken": "Programmierung, logisches Denken, Problemlösung und Lernen."
            }
        }

        rolle = self.values[0]
        vorlage = vorlagen[rolle]

        await interaction.response.send_modal(
            BewerbungModal(
                rolle=rolle,
                motivation_vorlage=vorlage["motivation"],
                staerken_vorlage=vorlage["staerken"],
                erfahrung_vorlage=vorlage["erfahrung"]
            )
        )


# =========================================================
# BEWERBUNGS-VIEW
# =========================================================

class BewerbungView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Supporter",
        emoji="💬",
        style=discord.ButtonStyle.primary,
        custom_id="bewerbung_supporter"
    )
    async def supporter(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            BewerbungModal(
                "Supporter",
                "Ich helfe gerne anderen Usern und möchte das Team im Support unterstützen.",
                "Hilfsbereitschaft, Geduld, Kommunikation und Zuverlässigkeit.",
                "Ich habe Erfahrung darin, anderen bei Fragen oder Problemen zu helfen."
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            BewerbungModal(
                "Moderator",
                "Ich möchte dabei helfen, dass der Server freundlich, fair und ordentlich bleibt.",
                "Kommunikation, Geduld, Regelkenntnis und Konfliktlösung.",
                "Ich habe Erfahrung mit Moderation, Regelwerken oder Discord-Servern."
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            BewerbungModal(
                "Entwickler",
                "Ich möchte bei technischen Projekten helfen und neue Funktionen entwickeln.",
                "Programmierung, logisches Denken, Problemlösung und Lernen.",
                "Ich habe Erfahrung mit Programmierung und Entwicklung."
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            BewerbungModal(
                "Admin",
                "Ich möchte Verantwortung übernehmen und das Team bei der Organisation unterstützen.",
                "Organisation, Verantwortungsbewusstsein und Teamarbeit.",
                "Ich habe Erfahrung mit Organisation, Verantwortung oder Teamleitung."
            )
        )

    @discord.ui.select(
        AutomatischesFormular()
    )
    async def rolle_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select
    ):
        pass


# =========================================================
# /bewerbung
# =========================================================

@tree.command(
    name="bewerbung",
    description="Sendet das Bewerbungsformular"
)
async def bewerbung(
    interaction: discord.Interaction
):

    if not await check_admin(interaction):
        return

    embed = discord.Embed(
        title="📋 Team-Bewerbung",
        description=(
            "Du möchtest dem Team beitreten?\n\n"
            "Wähle unten deine gewünschte Position aus "
            "und fülle anschließend das Formular aus."
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
# /ping
# =========================================================

@tree.command(
    name="ping",
    description="Zeigt die aktuelle Bot-Latenz"
)
async def ping(
    interaction: discord.Interaction
):

    latency = bot.latency * 1000

    await interaction.response.send_message(
        f"🏓 **Pong!**\n"
        f"🤖 Discord-Latenz: `{latency:.0f} ms`",
        ephemeral=True
    )


# =========================================================
# WEBSITE PING
# =========================================================

def check_website():

    if not WEBSITE_URL:
        return None, None, "WEBSITE_URL nicht gesetzt"

    try:
        start = time.perf_counter()

        response = requests.get(
            WEBSITE_URL,
            timeout=10
        )

        elapsed = (time.perf_counter() - start) * 1000

        return (
            response.status_code,
            elapsed,
            "OK"
        )

    except requests.RequestException as error:

        return (
            None,
            None,
            str(error)
        )


# =========================================================
# /bot status
# =========================================================

@tree.command(
    name="status",
    description="Zeigt den Echtzeitstatus von Bot und Website"
)
async def status(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    discord_latency = bot.latency * 1000

    website_status, website_ping, website_error = await asyncio.to_thread(
        check_website
    )

    # Discord Status
    if bot.is_ready():
        bot_status = "🟢 Online"
    else:
        bot_status = "🔴 Offline"

    # Website Status
    if website_status is not None and 200 <= website_status < 400:
        website_text = (
            f"🟢 Online\n"
            f"HTTP: `{website_status}`\n"
            f"Ping: `{website_ping:.0f} ms`"
        )
    elif website_status is not None:
        website_text = (
            f"🟠 Antwort erhalten\n"
            f"HTTP: `{website_status}`\n"
            f"Ping: `{website_ping:.0f} ms`"
        )
    else:
        website_text = (
            f"🔴 Nicht erreichbar\n"
            f"`{website_error}`"
        )

    # Netzwerkstatus
    if discord_latency < 100:
        network_status = "🟢 Sehr gut"
    elif discord_latency < 250:
        network_status = "🟡 Normal"
    elif discord_latency < 500:
        network_status = "🟠 Langsam"
    else:
        network_status = "🔴 Sehr langsam"

    embed = discord.Embed(
        title="📡 Echtzeit-Systemstatus",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🤖 Discord Bot",
        value=(
            f"{bot_status}\n"
            f"WebSocket: `{discord_latency:.0f} ms`"
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
            f"{network_status}\n"
            f"Discord Ping: `{discord_latency:.0f} ms`"
        ),
        inline=True
    )

    embed.add_field(
        name="⏱️ Bot-Uptime",
        value=f"`{format_uptime()}`",
        inline=False
    )

    embed.add_field(
        name="📋 Blocklist",
        value=f"`{len(blocklist)}` User",
        inline=True
    )

    embed.add_field(
        name="✅ Whitelist",
        value=f"`{len(whitelist)}` User",
        inline=True
    )

    embed.set_footer(
        text="Live-Status"
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# /blocklist
# =========================================================

@tree.command(
    name="blocklist",
    description="Zeigt die aktuelle Blocklist"
)
async def blocklist_command(
    interaction: discord.Interaction
):

    if not await check_admin(interaction):
        return

    if not blocklist:
        text = "Die Blocklist ist leer."
    else:
        text = "\n".join(
            f"• `{user_id}`"
            for user_id in blocklist
        )

    await interaction.response.send_message(
        f"🚫 **Blocklist**\n\n{text}",
        ephemeral=True
    )


# =========================================================
# /whitelist
# =========================================================

@tree.command(
    name="whitelist",
    description="Zeigt die aktuelle Whitelist"
)
async def whitelist_command(
    interaction: discord.Interaction
):

    if not await check_admin(interaction):
        return

    if not whitelist:
        text = "Die Whitelist ist leer."
    else:
        text = "\n".join(
            f"• `{user_id}`"
            for user_id in whitelist
        )

    await interaction.response.send_message(
        f"✅ **Whitelist**\n\n{text}",
        ephemeral=True
    )


# =========================================================
# /disconnect
# =========================================================

@tree.command(
    name="disconnect",
    description="Trennt den Bot von Discord"
)
async def disconnect(
    interaction: discord.Interaction
):

    if not is_owner(interaction):
        await interaction.response.send_message(
            "❌ Nur der Owner darf diesen Befehl benutzen.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔌 **Bot wird von Discord getrennt...**",
        ephemeral=True
    )

    await bot.close()


# =========================================================
# /restart
# =========================================================

@tree.command(
    name="restart",
    description="Startet den Render-Service wirklich neu"
)
async def restart(
    interaction: discord.Interaction
):

    if not is_owner(interaction):
        await interaction.response.send_message(
            "❌ Du darfst diesen Befehl nicht benutzen.",
            ephemeral=True
        )
        return

    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        await interaction.response.send_message(
            "❌ Render API ist nicht konfiguriert.",
            ephemeral=True
        )
        return

    # Nachricht ZUERST senden.
    # Danach wird Render neu gestartet.
    await interaction.response.send_message(
        "🔄 **Render-Neustart wird jetzt ausgelöst...**\n"
        "⏳ Der Bot startet gleich neu.",
        ephemeral=True
    )

    url = (
        f"https://api.render.com/v1/services/"
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

    print("=" * 50)
    print(f"🤖 Eingeloggt als: {bot.user}")
    print(f"🆔 Bot-ID: {bot.user.id}")
    print(f"📡 Discord Ping: {bot.latency * 1000:.0f} ms")
    print("=" * 50)

    # Persistent View registrieren
    try:
        bot.add_view(
            BewerbungView()
        )

        print(
            "✅ Bewerbungs-View registriert."
        )

    except Exception as error:

        print(
            f"❌ Fehler bei View: {error}"
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
            f"❌ Fehler beim Sync der Commands: {error}"
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN fehlt!"
        )

    print("🌐 Starte Flask-Webserver...")

    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    print("🤖 Starte Discord Bot...")

    bot.run(TOKEN)
