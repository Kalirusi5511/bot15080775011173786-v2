import os
import threading
import requests

import discord
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BEWERBUNGS_CHANNEL_ID = int(
    os.getenv("BEWERBUNGS_CHANNEL_ID", "0")
)

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")


# =========================================================
# FLASK / RENDER
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
    app.run(host="0.0.0.0", port=port)


threading.Thread(
    target=run_web,
    daemon=True
).start()


# =========================================================
# DISCORD
# =========================================================

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt!")

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# BEWERBUNGS-FORMULAR
# =========================================================

class BewerbungModal(discord.ui.Modal):

    def __init__(
        self,
        bereich,
        motivation_vorlage=""
    ):
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
            label="Erfahrung",
            placeholder="Was hast du schon gemacht?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )

        self.motivation = discord.ui.TextInput(
            label="Warum möchtest du dich bewerben?",
            placeholder="z.B. Weil ich gut im Coden bin...",
            default=motivation_vorlage,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=700
        )

        self.staerken = discord.ui.TextInput(
            label="Deine Stärken",
            placeholder="z.B. Teamwork, freundlich, aktiv...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )

        self.add_item(self.alter)
        self.add_item(self.erfahrung)
        self.add_item(self.motivation)
        self.add_item(self.staerken)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        # =====================================================
        # CHANNEL ABRUFEN
        # =====================================================

        if BEWERBUNGS_CHANNEL_ID == 0:
            await interaction.response.send_message(
                "❌ **BEWERBUNGS_CHANNEL_ID fehlt!**\n"
                "Prüfe die Environment Variables in Render.",
                ephemeral=True
            )
            return

        try:
            channel = await interaction.client.fetch_channel(
                BEWERBUNGS_CHANNEL_ID
            )

        except discord.NotFound:
            print(
                f"❌ CHANNEL NICHT GEFUNDEN: "
                f"{BEWERBUNGS_CHANNEL_ID}"
            )

            await interaction.response.send_message(
                f"❌ **Channel nicht gefunden!**\n\n"
                f"🔢 ID: `{BEWERBUNGS_CHANNEL_ID}`\n\n"
                f"Prüfe, ob die Channel-ID korrekt ist.",
                ephemeral=True
            )
            return

        except discord.Forbidden:
            print(
                f"🔒 KEINE BERECHTIGUNG: "
                f"{BEWERBUNGS_CHANNEL_ID}"
            )

            await interaction.response.send_message(
                f"🔒 **Keine Berechtigung!**\n\n"
                f"🔢 ID: `{BEWERBUNGS_CHANNEL_ID}`\n\n"
                f"Der Bot kann diesen Channel nicht sehen.",
                ephemeral=True
            )
            return

        except discord.HTTPException as error:
            print(
                f"⚠️ Discord API Fehler: {error}"
            )

            await interaction.response.send_message(
                f"⚠️ **Discord API Fehler!**\n\n"
                f"`{error}`",
                ephemeral=True
            )
            return

        # =====================================================
        # BEWERBUNG
        # =====================================================

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            description=(
                f"**Bewerber:** {interaction.user.mention}\n"
                f"**Bereich:** {self.bereich}"
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

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        # =====================================================
        # SENDEN
        # =====================================================

        try:
            await channel.send(embed=embed)

            print(
                f"✅ Bewerbung von {interaction.user} "
                f"erfolgreich gesendet."
            )

            await interaction.response.send_message(
                "✅ **Deine Bewerbung wurde abgeschickt!**",
                ephemeral=True
            )

        except discord.Forbidden:
            print(
                f"🔒 BOT KANN NICHT SCHREIBEN: "
                f"{BEWERBUNGS_CHANNEL_ID}"
            )

            await interaction.response.send_message(
                "🔒 **Der Bot darf dort nicht schreiben.**\n\n"
                "Benötigt werden:\n"
                "• Channel ansehen\n"
                "• Nachrichten senden\n"
                "• Links einbetten",
                ephemeral=True
            )

        except Exception as error:
            print(
                f"🔥 Bewerbungsfehler: "
                f"{type(error).__name__}: {error}"
            )

            await interaction.response.send_message(
                f"❌ **Fehler beim Absenden!**\n\n"
                f"`{type(error).__name__}: {error}`",
                ephemeral=True
            )


# =========================================================
# AUTOMATISCHE FORMULAR-VORLAGEN
# =========================================================

class AutomatischesFormular(
    discord.ui.Select
):

    def __init__(self):

        options = [
            discord.SelectOption(
                label="Coding",
                description="Vorlage für Entwickler",
                emoji="👨‍💻",
                value="coding"
            ),
            discord.SelectOption(
                label="Moderation",
                description="Vorlage für Moderatoren",
                emoji="🛡️",
                value="moderation"
            ),
            discord.SelectOption(
                label="Support",
                description="Vorlage für Supporter",
                emoji="💬",
                value="support"
            ),
            discord.SelectOption(
                label="Teamwork",
                description="Allgemeine Team-Vorlage",
                emoji="🤝",
                value="teamwork"
            )
        ]

        super().__init__(
            placeholder="✨ Automatisches Formular auswählen...",
            options=options,
            custom_id="automatisches_formular"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        vorlagen = {

            "coding": (
                "Ich möchte mich bewerben, weil ich "
                "gerne programmiere und gut im Coden bin. "
                "Ich möchte meine Kenntnisse im Team "
                "einbringen und weiterentwickeln."
            ),

            "moderation": (
                "Ich möchte mich als Moderator bewerben, "
                "weil ich gerne anderen helfe und auf "
                "einem Server für Ordnung sorgen möchte."
            ),

            "support": (
                "Ich möchte mich als Supporter bewerben, "
                "weil ich gerne anderen bei Problemen helfe "
                "und freundlich mit Usern umgehe."
            ),

            "teamwork": (
                "Ich möchte mich bewerben, weil ich gerne "
                "im Team arbeite, aktiv bin und das Team "
                "unterstützen möchte."
            )
        }

        texte = vorlagen[self.values[0]]

        bereiche = {
            "coding": "Entwickler",
            "moderation": "Moderator",
            "support": "Supporter",
            "teamwork": "Supporter"
        }

        await interaction.response.send_modal(
            BewerbungModal(
                bereiche[self.values[0]],
                texte
            )
        )


# =========================================================
# BUTTONS + MENÜ
# =========================================================

class BewerbungView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            AutomatischesFormular()
        )

    @discord.ui.button(
        label="Supporter",
        emoji="🛡️",
        style=discord.ButtonStyle.secondary,
        custom_id="bewerbung_supporter"
    )
    async def supporter(
        self,
        interaction,
        button
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
        interaction,
        button
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
        interaction,
        button
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
        interaction,
        button
    ):
        await interaction.response.send_modal(
            BewerbungModal("Admin")
        )


# =========================================================
# /BEWERBUNG
# =========================================================

@bot.tree.command(
    name="bewerbung",
    description="Sendet das Bewerbungs-System"
)
async def bewerbung(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Du brauchst Administrator-Rechte.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎓 Bewerbungs-System",
        description=(
            "Willkommen im Bewerbungs-System! 📝\n\n"
            "Wähle einen Bereich:\n\n"
            "🛡️ **Supporter**\n"
            "🛡️ **Moderator**\n"
            "👨‍💻 **Entwickler**\n"
            "👑 **Admin**\n\n"
            "Oder benutze unten das Menü für "
            "eine automatische Formular-Vorlage."
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
# /PING
# =========================================================

@bot.tree.command(
    name="ping",
    description="Zeigt die Bot-Latenz"
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🏓 **Pong!**\n"
        f"📡 Latenz: `{latency}ms`"
    )


# =========================================================
# /RESTART
# =========================================================

@bot.tree.command(
    name="restart",
    description="Startet den Render-Service neu"
)
async def restart(
    interaction: discord.Interaction
):

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
            print("✅ Render-Restart gestartet.")

        else:
            print(
                f"❌ Render API Fehler: "
                f"{response.status_code}"
            )
            print(response.text)

    except requests.RequestException as error:

        print(
            f"❌ Render API Fehler: {error}"
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    print("======================================")
    print(f"🤖 Bot: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(
        f"📨 Bewerbungs-Channel: "
        f"{BEWERBUNGS_CHANNEL_ID}"
    )
    print("🚀 Bot ist online!")
    print("======================================")

    try:
        bot.add_view(BewerbungView())
    except Exception as error:
        print(
            f"❌ View Fehler: {error}"
        )

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

print("🚀 Discord Bot startet...")

bot.run(TOKEN)
