```python
import os
import threading
import requests

from flask import Flask
import discord
from discord.ext import commands
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


# =========================================================
# CHECK CONFIG
# =========================================================

if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN fehlt!")

if not BEWERBUNGS_CHANNEL_ID:
    raise RuntimeError("❌ BEWERBUNGS_CHANNEL_ID fehlt!")

if not OWNER_ID:
    raise RuntimeError("❌ OWNER_ID fehlt!")


# =========================================================
# FLASK / RENDER HEALTH CHECK
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Discord Bot läuft! ✅", 200


@app.route("/health")
def health():
    return "OK", 200


def run_web():
    port = int(os.getenv("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port
    )


threading.Thread(
    target=run_web,
    daemon=True
).start()


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# BEWERBUNGS MODAL
# =========================================================

class BewerbungModal(discord.ui.Modal):

    def __init__(self, bereich: str):
        super().__init__(
            title=f"Bewerbung: {bereich}"
        )

        self.bereich = bereich

        self.alter = discord.ui.TextInput(
            label="Wie alt bist du?",
            placeholder="z.B. 15",
            required=True,
            max_length=3
        )

        self.erfahrung = discord.ui.TextInput(
            label="Deine Erfahrung",
            placeholder="Welche Erfahrungen hast du?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.motivation = discord.ui.TextInput(
            label="Warum möchtest du dich bewerben?",
            placeholder="Erkläre deine Motivation...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        self.staerken = discord.ui.TextInput(
            label="Deine Stärken",
            placeholder="z.B. Teamwork, Aktivität, Kommunikation...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.zusatz = discord.ui.TextInput(
            label="Weitere Informationen",
            placeholder="Optional",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )

        self.add_item(self.alter)
        self.add_item(self.erfahrung)
        self.add_item(self.motivation)
        self.add_item(self.staerken)
        self.add_item(self.zusatz)

    async def on_submit(self, interaction: discord.Interaction):

        channel = interaction.client.get_channel(
            BEWERBUNGS_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Bewerbungs-Channel wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            description=(
                f"**Bereich:** {self.bereich}\n"
                f"**Bewerber:** {interaction.user.mention}"
            ),
            color=discord.Color.blurple()
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
            name="💡 Motivation",
            value=self.motivation.value,
            inline=False
        )

        embed.add_field(
            name="⭐ Stärken",
            value=self.staerken.value,
            inline=False
        )

        if self.zusatz.value:
            embed.add_field(
                name="📝 Weitere Informationen",
                value=self.zusatz.value,
                inline=False
            )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich abgeschickt!",
            ephemeral=True
        )


# =========================================================
# BEWERBUNGS BUTTONS
# =========================================================

class BewerbungView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Supporter",
        emoji="🛡️",
        style=discord.ButtonStyle.secondary,
        custom_id="bewerbung_supporter"
    )
    async def supporter(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            BewerbungModal("Supporter")
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
            BewerbungModal("Moderator")
        )

    @discord.ui.button(
        label="Entwickler",
        emoji="👨‍💻",
        style=discord.ButtonStyle.success,
        custom_id="bewerbung_entwickler"
    )
    async def entwickler(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            BewerbungModal("Entwickler")
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
            BewerbungModal("Admin")
        )


# =========================================================
# /bewerbung
# =========================================================

@bot.tree.command(
    name="bewerbung",
    description="Sendet das Bewerbungs-System"
)
async def bewerbung(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Du brauchst Administrator-Rechte.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎓 Bewerbungs System",
        description=(
            "Willkommen zum Bewerbungs-System.\n\n"
            "🛡️ **Supporter**\n"
            "🛡️ **Moderator**\n"
            "👨‍💻 **Entwickler**\n"
            "👑 **Admin**\n\n"
            "Klicke auf einen Button."
        ),
        color=discord.Color.blurple()
    )

    await interaction.channel.send(
        embed=embed,
        view=BewerbungView()
    )

    await interaction.response.send_message(
        "✅ Bewerbungs-System wurde gesendet.",
        ephemeral=True
    )


# =========================================================
# /ping
# =========================================================

@bot.tree.command(
    name="ping",
    description="Zeigt die Bot-Latenz"
)
async def ping(interaction: discord.Interaction):

    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🏓 **Pong!**\n"
        f"📡 Latenz: `{latency}ms`"
    )


# =========================================================
# /restart
# =========================================================

@bot.tree.command(
    name="restart",
    description="Startet den Render-Service neu"
)
async def restart(interaction: discord.Interaction):

    # Nur OWNER_ID
    if interaction.user.id != OWNER_ID:
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

    await interaction.response.send_message(
        "🔄 **Render-Service wird neu gestartet...**",
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

        if response.status_code == 200:

            print("✅ Render-Service wird neu gestartet.")

        else:

            print(
                f"❌ Render Fehler "
                f"{response.status_code}: "
                f"{response.text}"
            )

    except requests.RequestException as error:

        print(
            f"❌ Render API Fehler: {error}"
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"🤖 Bot: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print("====================================")

    # Persistent Buttons registrieren
    bot.add_view(BewerbungView())

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} Slash Commands synchronisiert."
        )

    except Exception as error:

        print(
            f"❌ Slash Command Fehler: {error}"
        )


# =========================================================
# START
# =========================================================

print("🚀 Bot startet...")

bot.run(TOKEN)
```
