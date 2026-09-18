import os
import threading
import requests
from datetime import datetime, timezone

import discord
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
except ValueError:
    OWNER_ID = 0

try:
    BEWERBUNGS_CHANNEL_ID = int(
        os.getenv("BEWERBUNGS_CHANNEL_ID", "0")
    )
except ValueError:
    BEWERBUNGS_CHANNEL_ID = 0

START_TIME = datetime.now(timezone.utc)

blocklist = set()
whitelist = set()


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

    app.run(
        host="0.0.0.0",
        port=port
    )


threading.Thread(
    target=run_web,
    daemon=True
).start()


# =========================================================
# DISCORD BOT
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN fehlt in den Environment Variables!"
    )


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
        motivation_vorlage="",
        staerken_vorlage="",
        erfahrung_vorlage=""
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
            default=erfahrung_vorlage,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )

        self.motivation = discord.ui.TextInput(
            label="Warum möchtest du dich bewerben?",
            placeholder="Warum möchtest du ins Team?",
            default=motivation_vorlage,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=700
        )

        self.staerken = discord.ui.TextInput(
            label="Deine Stärken",
            placeholder="z.B. Teamwork, freundlich, aktiv...",
            default=staerken_vorlage,
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
        # ID PRÜFEN
        # =====================================================

        if BEWERBUNGS_CHANNEL_ID == 0:

            print(
                "❌ BEWERBUNGS_CHANNEL_ID ist 0 oder fehlt."
            )

            await interaction.response.send_message(
                "❌ **Bewerbungs-Channel ist nicht konfiguriert!**\n\n"
                "Die Environment Variable "
                "`BEWERBUNGS_CHANNEL_ID` fehlt oder ist ungültig.",
                ephemeral=True
            )
            return

        # =====================================================
        # CHANNEL ABRUFEN
        # =====================================================

        try:

            channel = await interaction.client.fetch_channel(
                BEWERBUNGS_CHANNEL_ID
            )

            print(
                f"✅ Bewerbungs-Channel gefunden: "
                f"{channel} ({channel.id})"
            )

        except discord.NotFound:

            print(
                "❌ CHANNEL NICHT GEFUNDEN"
            )

            print(
                f"Verwendete ID: "
                f"{BEWERBUNGS_CHANNEL_ID}"
            )

            await interaction.response.send_message(
                "❌ **Channel nicht gefunden!**\n\n"
                f"🔢 Channel-ID:\n"
                f"`{BEWERBUNGS_CHANNEL_ID}`\n\n"
                "Mögliche Gründe:\n"
                "• Die ID ist falsch.\n"
                "• Der Channel wurde gelöscht.\n"
                "• Die ID gehört nicht zu einem Channel.\n"
                "• Der Channel befindet sich auf einem Server, "
                "auf dem der Bot nicht ist.",
                ephemeral=True
            )
            return

        except discord.Forbidden:

            print(
                "🔒 KEINE BERECHTIGUNG FÜR CHANNEL"
            )

            print(
                f"Channel-ID: "
                f"{BEWERBUNGS_CHANNEL_ID}"
            )

            await interaction.response.send_message(
                "🔒 **Der Bot hat keinen Zugriff auf diesen Channel!**\n\n"
                f"🔢 ID: `{BEWERBUNGS_CHANNEL_ID}`\n\n"
                "Prüfe die Berechtigungen des Bots:\n"
                "• Channel ansehen\n"
                "• Nachrichten senden\n"
                "• Links einbetten",
                ephemeral=True
            )
            return

        except discord.HTTPException as error:

            print(
                f"⚠️ DISCORD API FEHLER: "
                f"{type(error).__name__}: {error}"
            )

            await interaction.response.send_message(
                "⚠️ **Discord konnte den Channel nicht laden!**\n\n"
                f"Fehler: `{type(error).__name__}`\n"
                f"Details: `{error}`\n\n"
                f"Channel-ID: `{BEWERBUNGS_CHANNEL_ID}`",
                ephemeral=True
            )
            return

        # =====================================================
        # BEWERBUNGS-EMBED
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
        # BEWERBUNG SENDEN
        # =====================================================

        try:

            await channel.send(
                embed=embed
            )

            print(
                f"✅ Bewerbung von "
                f"{interaction.user} erfolgreich gesendet."
            )

            await interaction.response.send_message(
                "✅ **Deine Bewerbung wurde erfolgreich abgeschickt!**",
                ephemeral=True
            )

        except discord.Forbidden:

            print(
                f"🔒 BOT KANN NICHT SCHREIBEN: "
                f"{BEWERBUNGS_CHANNEL_ID}"
            )

            await interaction.response.send_message(
                "🔒 **Der Bot darf in diesen Channel nicht schreiben!**\n\n"
                f"🔢 Channel-ID: `{BEWERBUNGS_CHANNEL_ID}`\n\n"
                "Benötigte Berechtigungen:\n"
                "• Channel ansehen\n"
                "• Nachrichten senden\n"
                "• Links einbetten",
                ephemeral=True
            )

        except discord.HTTPException as error:

            print(
                f"⚠️ SEND-FEHLER: "
                f"{type(error).__name__}: {error}"
            )

            await interaction.response.send_message(
                "⚠️ **Die Bewerbung konnte nicht gesendet werden!**\n\n"
                f"Fehler: `{type(error).__name__}`\n"
                f"Details: `{error}`",
                ephemeral=True
            )

        except Exception as error:

            print(
                f"🔥 BEWERBUNGSFEHLER: "
                f"{type(error).__name__}: {error}"
            )

            await interaction.response.send_message(
                "❌ **Unerwarteter Fehler!**\n\n"
                f"`{type(error).__name__}: {error}`",
                ephemeral=True
            )


# =========================================================
# AUTOMATISCHE FORMULAR-VORLAGEN
# =========================================================

class AutomatischesFormular(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Admin",
                description="Automatische Admin-Bewerbung",
                emoji="👑",
                value="admin"
            ),

            discord.SelectOption(
                label="Moderator",
                description="Automatische Moderator-Bewerbung",
                emoji="🛡️",
                value="moderator"
            ),

            discord.SelectOption(
                label="Supporter",
                description="Automatische Supporter-Bewerbung",
                emoji="💬",
                value="supporter"
            ),

            discord.SelectOption(
                label="Entwickler",
                description="Automatische Entwickler-Bewerbung",
                emoji="👨‍💻",
                value="entwickler"
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

            # =================================================
            # ADMIN
            # =================================================

            "admin": {

                "bereich": "Admin",

                "erfahrung": (
                    "Ich habe Erfahrung mit Organisation, "
                    "Teamarbeit und dem Übernehmen von "
                    "Verantwortung."
                ),

                "motivation": (
                    "Ich möchte mich als Admin bewerben, "
                    "weil ich gerne Verantwortung übernehme, "
                    "das Team unterstütze und bei wichtigen "
                    "Aufgaben mithelfen möchte."
                ),

                "staerken": (
                    "Verantwortungsbewusst, organisiert, "
                    "zuverlässig, aktiv und teamfähig."
                )
            },

            # =================================================
            # MODERATOR
            # =================================================

            "moderator": {

                "bereich": "Moderator",

                "erfahrung": (
                    "Ich habe Erfahrung im Umgang mit Usern, "
                    "Regeln und dem Lösen von Problemen."
                ),

                "motivation": (
                    "Ich möchte mich als Moderator bewerben, "
                    "weil ich gerne anderen helfe, auf Regeln "
                    "achte und für ein angenehmes Serverklima "
                    "sorgen möchte."
                ),

                "staerken": (
                    "Geduldig, fair, freundlich, "
                    "kommunikativ und zuverlässig."
                )
            },

            # =================================================
            # SUPPORTER
            # =================================================

            "supporter": {

                "bereich": "Supporter",

                "erfahrung": (
                    "Ich habe Erfahrung darin, anderen bei "
                    "Fragen und Problemen zu helfen und "
                    "gemeinsam Lösungen zu finden."
                ),

                "motivation": (
                    "Ich möchte mich als Supporter bewerben, "
                    "weil ich gerne anderen helfe und User "
                    "bei ihren Problemen unterstützen möchte."
                ),

                "staerken": (
                    "Hilfsbereit, freundlich, geduldig, "
                    "kommunikativ und aktiv."
                )
            },

            # =================================================
            # ENTWICKLER
            # =================================================

            "entwickler": {

                "bereich": "Entwickler",

                "erfahrung": (
                    "Ich habe Erfahrung mit Programmierung "
                    "und habe bereits eigene Projekte, "
                    "Bots oder andere Programme erstellt."
                ),

                "motivation": (
                    "Ich möchte mich als Entwickler bewerben, "
                    "weil ich gerne programmiere und gut im "
                    "Coden bin. Ich möchte meine Kenntnisse "
                    "ins Team einbringen und weiterentwickeln."
                ),

                "staerken": (
                    "Programmierkenntnisse, logisches Denken, "
                    "Problemlösung, Kreativität und Teamarbeit."
                )
            }
        }

        value = self.values[0]
        vorlage = vorlagen[value]

        await interaction.response.send_modal(
            BewerbungModal(
                vorlage["bereich"],
                vorlage["motivation"],
                vorlage["staerken"],
                vorlage["erfahrung"]
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

        self.add_item(
            AutomatischesFormular()
        )

    # =====================================================
    # SUPPORTER
    # =====================================================

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

    # =====================================================
    # MODERATOR
    # =====================================================

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

    # =====================================================
    # ENTWICKLER
    # =====================================================

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

    # =====================================================
    # ADMIN
    # =====================================================

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
            "Oder benutze das Menü unten für "
            "eine automatische Formular-Vorlage.\n\n"
            "✨ Die automatische Vorlage füllt "
            "Erfahrung, Motivation und Stärken "
            "passend zur Rolle voraus."
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

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 **Pong!**\n"
        f"📡 Latenz: `{latency}ms`"
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
    description="Zeigt den Status des Bots"
)
async def bot_status(
    interaction: discord.Interaction
):

    if interaction.user.id != OWNER_ID:

        await interaction.response.send_message(
            "❌ Nur der Bot-Owner darf diesen Befehl benutzen.",
            ephemeral=True
        )
        return

    uptime = (
        datetime.now(timezone.utc)
        - START_TIME
    )

    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🟢 Status",
        value="Online",
        inline=True
    )

    embed.add_field(
        name="📡 Ping",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    embed.add_field(
        name="🌐 Server",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=str(uptime).split(".")[0],
        inline=False
    )

    embed.add_field(
        name="🚫 Blocklist",
        value=str(len(blocklist)),
        inline=True
    )

    embed.add_field(
        name="✅ Whitelist",
        value=str(len(whitelist)),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# /BOT DISCONNECT
# =========================================================

@bot_group.command(
    name="disconnect",
    description="Trennt den Bot vom Discord Gateway"
)
async def bot_disconnect(
    interaction: discord.Interaction
):

    if interaction.user.id != OWNER_ID:

        await interaction.response.send_message(
            "❌ Nur der Bot-Owner darf diesen Befehl benutzen.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "🔌 **Bot wird getrennt...**",
        ephemeral=True
    )

    print(
        "🔌 Disconnect wurde vom Owner ausgelöst."
    )

    await bot.close()


# =========================================================
# /BOT BLOCKLIST
# =========================================================

@bot_group.command(
    name="blocklist",
    description="Verwaltet die Blocklist"
)
@discord.app_commands.describe(
    action="Aktion",
    user="Discord User"
)
@discord.app_commands.choices(
    action=[
        discord.app_commands.Choice(
            name="add",
            value="add"
        ),
        discord.app_commands.Choice(
            name="remove",
            value="remove"
        ),
        discord.app_commands.Choice(
            name="list",
            value="list"
        )
    ]
)
async def bot_blocklist(
    interaction: discord.Interaction,
    action: str,
    user: discord.User = None
):

    if interaction.user.id != OWNER_ID:

        await interaction.response.send_message(
            "❌ Nur der Bot-Owner darf diesen Befehl benutzen.",
            ephemeral=True
        )
        return

    # LIST

    if action == "list":

        if not blocklist:

            await interaction.response.send_message(
                "🚫 Die Blocklist ist leer.",
                ephemeral=True
            )
            return

        users = "\n".join(
            f"• `{user_id}`"
            for user_id in blocklist
        )

        await interaction.response.send_message(
            f"🚫 **Blocklist**\n\n{users}",
            ephemeral=True
        )
        return

    # ADD

    if action == "add":

        if user is None:

            await interaction.response.send_message(
                "❌ Du musst einen User auswählen.",
                ephemeral=True
            )
            return

        blocklist.add(
            user.id
        )

        await interaction.response.send_message(
            f"🚫 {user.mention} wurde zur Blocklist hinzugefügt.",
            ephemeral=True
        )
        return

    # REMOVE

    if action == "remove":

        if user is None:

            await interaction.response.send_message(
                "❌ Du musst einen User auswählen.",
                ephemeral=True
            )
            return

        blocklist.discard(
            user.id
        )

        await interaction.response.send_message(
            f"✅ {user.mention} wurde von der Blocklist entfernt.",
            ephemeral=True
        )


# =========================================================
# /BOT WHITELIST
# =========================================================

@bot_group.command(
    name="whitelist",
    description="Verwaltet die Whitelist"
)
@discord.app_commands.describe(
    action="Aktion",
    user="Discord User"
)
@discord.app_commands.choices(
    action=[
        discord.app_commands.Choice(
            name="add",
            value="add"
        ),
        discord.app_commands.Choice(
            name="remove",
            value="remove"
        ),
        discord.app_commands.Choice(
            name="list",
            value="list"
        )
    ]
)
async def bot_whitelist(
    interaction: discord.Interaction,
    action: str,
    user: discord.User = None
):

    if interaction.user.id != OWNER_ID:

        await interaction.response.send_message(
            "❌ Nur der Bot-Owner darf diesen Befehl benutzen.",
            ephemeral=True
        )
        return

    # LIST

    if action == "list":

        if not whitelist:

            await interaction.response.send_message(
                "✅ Die Whitelist ist leer.",
                ephemeral=True
            )
            return

        users = "\n".join(
            f"• `{user_id}`"
            for user_id in whitelist
        )

        await interaction.response.send_message(
            f"✅ **Whitelist**\n\n{users}",
            ephemeral=True
        )
        return

    # ADD

    if action == "add":

        if user is None:

            await interaction.response.send_message(
                "❌ Du musst einen User auswählen.",
                ephemeral=True
            )
            return

        whitelist.add(
            user.id
        )

        await interaction.response.send_message(
            f"✅ {user.mention} wurde zur Whitelist hinzugefügt.",
            ephemeral=True
        )
        return

    # REMOVE

    if action == "remove":

        if user is None:

            await interaction.response.send_message(
                "❌ Du musst einen User auswählen.",
                ephemeral=True
            )
            return

        whitelist.discard(
            user.id
        )

        await interaction.response.send_message(
            f"✅ {user.mention} wurde von der Whitelist entfernt.",
            ephemeral=True
        )


# =========================================================
# BOT GRUPPE REGISTRIEREN
# =========================================================

bot.tree.add_command(
    bot_group
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

    if not RENDER_API_KEY:

        await interaction.response.send_message(
            "❌ **RENDER_API_KEY fehlt!**",
            ephemeral=True
        )
        return

    if not RENDER_SERVICE_ID:

        await interaction.response.send_message(
            "❌ **RENDER_SERVICE_ID fehlt!**",
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

            print(
                "✅ Render-Restart gestartet."
            )

        else:

            print(
                f"❌ Render API Fehler: "
                f"{response.status_code}"
            )

            print(
                response.text
            )

    except requests.RequestException as error:

        print(
            f"❌ Render API Fehler: "
            f"{error}"
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    print(
        "======================================"
    )

    print(
        f"🤖 Bot: {bot.user}"
    )

    print(
        f"🆔 ID: {bot.user.id}"
    )

    print(
        f"📨 Bewerbungs-Channel: "
        f"{BEWERBUNGS_CHANNEL_ID}"
    )

    print(
        f"🌐 Server: "
        f"{len(bot.guilds)}"
    )

    print(
        "🚀 Bot ist online!"
    )

    print(
        "======================================"
    )

    # =====================================================
    # PERSISTENTE BUTTONS
    # =====================================================

    try:

        bot.add_view(
            BewerbungView()
        )

        print(
            "✅ Bewerbungs-Buttons registriert."
        )

    except Exception as error:

        print(
            f"❌ View Fehler: "
            f"{type(error).__name__}: {error}"
        )

    # =====================================================
    # SLASH COMMANDS
    # =====================================================

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} Slash Commands synchronisiert."
        )

        for command in synced:

            print(
                f"   /{command.name}"
            )

    except Exception as error:

        print(
            f"❌ Slash Command Fehler: "
            f"{type(error).__name__}: {error}"
        )


# =========================================================
# START
# =========================================================

print(
    "🚀 Discord Bot startet..."
)

bot.run(TOKEN)
