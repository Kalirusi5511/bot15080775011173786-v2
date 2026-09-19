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
BEWERBUNGS_CHANNEL_ID = int(os.getenv("BEWERBUNGS_CHANNEL_ID", "0"))

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")

WEBSITE_URL = os.getenv("WEBSITE_URL", "")
PORT = int(os.getenv("PORT", "10000"))


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt!")

if OWNER_ID == 0:
    print("⚠️ OWNER_ID ist nicht gesetzt.")


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

bot = discord.Client(intents=intents)
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


def uptime():
    seconds = int(time.time() - START_TIME)

    days = seconds // 86400
    seconds %= 86400

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    seconds %= 60

    return f"{days}d {hours}h {minutes}m {seconds}s"


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
# BEWERBUNG MODAL
# =========================================================

class BewerbungModal(discord.ui.Modal):
    def __init__(self, rolle: str):
        super().__init__(title=f"Bewerbung – {rolle}")

        self.rolle = rolle

        self.name = discord.ui.TextInput(
            label="Name",
            placeholder="Dein Name",
            required=True,
            max_length=100
        )

        self.alter = discord.ui.TextInput(
            label="Alter",
            placeholder="Dein Alter",
            required=True,
            max_length=3
        )

        self.erfahrung = discord.ui.TextInput(
            label="Erfahrung",
            placeholder="Hast du bereits Erfahrung?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.motivation = discord.ui.TextInput(
            label="Warum möchtest du dich bewerben?",
            placeholder="Erzähl uns etwas über deine Motivation.",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        self.add_item(self.name)
        self.add_item(self.alter)
        self.add_item(self.erfahrung)
        self.add_item(self.motivation)

    async def on_submit(self, interaction: discord.Interaction):
        channel = bot.get_channel(BEWERBUNGS_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Bewerbungs-Channel wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Benutzer",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )

        embed.add_field(
            name="🎯 Bereich",
            value=self.rolle,
            inline=True
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
            name="📚 Erfahrung",
            value=self.erfahrung.value,
            inline=False
        )

        embed.add_field(
            name="💬 Motivation",
            value=self.motivation.value,
            inline=False
        )

        embed.set_footer(
            text="Bewerbungssystem"
        )

        try:
            await channel.send(embed=embed)

            await interaction.response.send_message(
                "✅ Deine Bewerbung wurde erfolgreich abgeschickt!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, im Bewerbungs-Channel zu schreiben.",
                ephemeral=True
            )

        except Exception as error:
            print(f"❌ Fehler beim Senden der Bewerbung: {error}")

            await interaction.response.send_message(
                "❌ Beim Absenden ist ein Fehler aufgetreten.",
                ephemeral=True
            )


# =========================================================
# BEWERBUNG SELECT
# =========================================================

class AutomatischesFormular(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Admin",
                value="Admin",
                emoji="👑"
            ),
            discord.SelectOption(
                label="Moderator",
                value="Moderator",
                emoji="🛡️"
            ),
            discord.SelectOption(
                label="Supporter",
                value="Supporter",
                emoji="💬"
            ),
            discord.SelectOption(
                label="Entwickler",
                value="Entwickler",
                emoji="💻"
            )
        ]

        super().__init__(
            placeholder="Wähle den Bereich deiner Bewerbung...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        rolle = self.values[0]

        await interaction.response.send_modal(
            BewerbungModal(rolle)
        )


# =========================================================
# BEWERBUNG VIEW
# =========================================================

class BewerbungView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(AutomatischesFormular())


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():
    global view_registered

    print("")
    print("===================================")
    print("🤖 BOT ONLINE")
    print(f"👤 Eingeloggt als: {bot.user}")
    print(f"🆔 Bot-ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)} ms")
    print("===================================")
    print("")

    # Persistent View nur EINMAL registrieren
    if not view_registered:
        bot.add_view(BewerbungView())
        view_registered = True
        print("✅ Bewerbung-View registriert.")

    # Slash Commands synchronisieren
    try:
        synced = await tree.sync()
        print(f"✅ {len(synced)} Slash Commands synchronisiert.")

    except Exception as error:
        print(f"❌ Fehler beim Synchronisieren der Commands: {error}")


# =========================================================
# DISCONNECT / RECONNECT
# =========================================================

@bot.event
async def on_disconnect():
    print("⚠️ Discord-Verbindung getrennt.")
    print("🔄 discord.py versucht automatisch, die Verbindung wiederherzustellen.")


@bot.event
async def on_resumed():
    print("✅ Discord-Verbindung erfolgreich wiederhergestellt.")
    print(f"📡 Ping: {round(bot.latency * 1000)} ms")


# =========================================================
# WATCHDOG
# =========================================================

async def discord_watchdog():
    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            if bot.is_ready():
                print(
                    f"💚 Watchdog: Bot läuft | "
                    f"Ping: {round(bot.latency * 1000)} ms"
                )
            else:
                print("⚠️ Watchdog: Bot ist momentan nicht bereit.")

        except Exception as error:
            print(f"⚠️ Watchdog-Fehler: {error}")

        await asyncio.sleep(60)


# =========================================================
# SETUP HOOK
# =========================================================

async def setup_hook():
    asyncio.create_task(discord_watchdog())


bot.setup_hook = setup_hook


# =========================================================
# /PING
# =========================================================

@tree.command(
    name="ping",
    description="Zeigt den Bot-Ping an."
)
async def ping(interaction: discord.Interaction):

    latency = round(bot.latency * 1000)

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
async def bewerbung(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📋 Bewerbungen",
        description=(
            "Du möchtest Teil unseres Teams werden?\n\n"
            "Wähle unten den Bereich aus, für den du dich "
            "bewerben möchtest."
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
# /BOT GRUPPE
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
async def bot_status(interaction: discord.Interaction):

    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )
        return

    latency = round(bot.latency * 1000)

    website = website_online()

    if website is None:
        website_status = "⚪ Nicht konfiguriert"
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
        value="🟢 Verbunden" if bot.is_ready() else "🔴 Getrennt",
        inline=False
    )

    embed.add_field(
        name="Ping",
        value=f"{latency} ms",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=uptime(),
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
async def bot_blocklist(interaction: discord.Interaction):

    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )
        return

    if not blocklist_users:
        text = "Keine Benutzer auf der Blocklist."
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
async def bot_whitelist(interaction: discord.Interaction):

    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )
        return

    if not whitelist_users:
        text = "Keine Benutzer auf der Whitelist."
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
async def bot_disconnect(interaction: discord.Interaction):

    if not is_owner(interaction.user.id):
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


tree.add_command(bot_group)


# =========================================================
# /RESTART
# =========================================================

@tree.command(
    name="restart",
    description="Startet den Render-Service neu."
)
async def restart(interaction: discord.Interaction):

    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )
        return

    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        await interaction.response.send_message(
            "❌ RENDER_API_KEY oder RENDER_SERVICE_ID fehlt.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔄 Render-Service wird neu gestartet...",
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
        response = requests.post(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code in (200, 201, 202, 204):
            print("✅ Render Restart erfolgreich ausgelöst.")
        else:
            print(
                f"❌ Render Restart fehlgeschlagen: "
                f"{response.status_code} {response.text}"
            )

    except requests.RequestException as error:
        print(f"❌ Fehler bei Render API: {error}")


# =========================================================
# GLOBAL ERROR HANDLER
# =========================================================

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ Discord Event Fehler: {event}")


# =========================================================
# START
# =========================================================

def main():

    # Flask parallel zum Discord-Bot starten
    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    print("🚀 Starte Discord Bot...")

    try:
        bot.run(TOKEN)

    except discord.LoginFailure:
        print("❌ DISCORD_TOKEN ist ungültig.")

    except KeyboardInterrupt:
        print("🛑 Bot manuell beendet.")

    except Exception as error:
        print(f"❌ Bot wurde beendet: {error}")


if __name__ == "__main__":
    main()
