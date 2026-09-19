import os
import time
import asyncio

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

PORT = int(
    os.getenv("PORT", "10000")
)


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
    print(
        "⚠️ BEWERBUNGS_CHANNEL_ID ist nicht gesetzt."
    )


# =========================================================
# FLASK / WSGI
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Discord Bot läuft! ✅", 200


@app.route("/health")
def health():
    return "OK", 200


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()

intents.members = True

bot = discord.Client(
    intents=intents
)

tree = discord.app_commands.CommandTree(
    bot
)


# =========================================================
# BOT STATUS
# =========================================================

BOT_AKTIV = True

WARTUNG_AKTIV = False

WARTUNGS_GRUND = "Regelmäßige Wartung"


# =========================================================
# SYSTEM
# =========================================================

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


def bot_status_text() -> str:

    if not BOT_AKTIV:

        return "🔴 **Bot ist ausgeschaltet.**"

    if WARTUNG_AKTIV:

        return "🟡 **Bot ist im Wartungsmodus.**"

    return "🟢 **Bot ist online und aktiv.**"


# =========================================================
# WARTUNGS-ANKÜNDIGUNG
# =========================================================

async def sende_wartungs_ankuendigung(
    interaction,
    aktiv: bool
):

    channel = bot.get_channel(
        BEWERBUNGS_CHANNEL_ID
    )

    if channel is None:

        print(
            "⚠️ Bewerbungs-Channel nicht gefunden."
        )

        return

    if aktiv:

        embed = discord.Embed(
            title="🛠️ WARTUNGSMODUS AKTIVIERT",
            description=(
                "**Der Bot wird momentan gewartet!**\n\n"
                "In dieser Zeit sind **keine Bewerbungen** möglich.\n"
                "Bitte habt etwas Geduld – wir sind bald wieder da! 🚀"
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="📋 Grund",
            value=WARTUNGS_GRUND,
            inline=False
        )

        embed.add_field(
            name="⏳ Status",
            value="Wartung läuft...",
            inline=True
        )

        embed.add_field(
            name="👤 Angekündigt von",
            value=interaction.user.mention,
            inline=True
        )

        embed.set_footer(
            text="Bewerbungssystem • Wartung"
        )

    else:

        embed = discord.Embed(
            title="✅ WARTUNG ABGESCHLOSSEN",
            description=(
                "**Der Bot ist wieder online!**\n\n"
                "Alle Funktionen stehen euch wieder zur Verfügung.\n"
                "Viel Erfolg beim Bewerben! 🎉"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Beendet von",
            value=interaction.user.mention,
            inline=True
        )

        embed.set_footer(
            text="Bewerbungssystem • Wartung beendet"
        )

    try:

        await channel.send(
            embed=embed
        )

        print(
            "📢 Wartungs-Ankündigung gesendet."
        )

    except Exception as error:

        print(
            f"❌ Ankündigung konnte nicht gesendet werden: {error}"
        )


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
        ),

        "auto_erfahrung": (
            "Ich habe Erfahrung mit Discord-Servern "
            "und Teamarbeit."
        ),

        "auto_motivation": (
            "Ich möchte Verantwortung übernehmen "
            "und den Server aktiv unterstützen."
        ),

        "auto_zusatz": (
            "Ich bin teamfähig, geduldig und "
            "kann gut mit Konflikten umgehen."
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
        ),

        "auto_erfahrung": (
            "Ich habe Erfahrung mit Moderation "
            "und kenne die Regeln gut."
        ),

        "auto_motivation": (
            "Ich möchte Moderator werden, "
            "um den Server freundlich und ordentlich zu halten."
        ),

        "auto_zusatz": (
            "Ich würde beide Seiten anhören "
            "und anschließend ruhig und fair handeln."
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
        ),

        "auto_erfahrung": (
            "Ich habe Erfahrung im Umgang mit Usern "
            "und helfe gerne bei Fragen."
        ),

        "auto_motivation": (
            "Ich möchte Supporter werden, weil ich "
            "anderen gerne helfe und geduldig bin."
        ),

        "auto_zusatz": (
            "Ich würde ruhig bleiben und versuchen, "
            "das Problem freundlich zu lösen."
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
        ),

        "auto_erfahrung": (
            "Ich kann Python und JavaScript "
            "und habe bereits Discord-Bots programmiert."
        ),

        "auto_motivation": (
            "Ich möchte Entwickler werden, "
            "um den Server mit nützlichen Features zu verbessern."
        ),

        "auto_zusatz": (
            "Ich habe bereits Discord-Bots "
            "und Webseiten programmiert."
        )
    }
}


# =========================================================
# BEWERBUNG MODAL
# =========================================================

class BewerbungModal(
    discord.ui.Modal
):

    def __init__(
        self,
        rolle: str,
        auto_fill: bool = False
    ):

        self.rolle = rolle

        self.auto_fill = auto_fill

        vorlage = FORMULAR_VORLAGEN.get(
            rolle,
            FORMULAR_VORLAGEN["Supporter"]
        )

        modus = (
            "Auto"
            if auto_fill
            else "Manuell"
        )

        super().__init__(
            title=f"{vorlage['beschreibung']} ({modus})"
        )

        self.name = discord.ui.TextInput(
            label="Name",
            placeholder="Gib deinen Namen ein...",
            required=True,
            max_length=100
        )

        self.alter = discord.ui.TextInput(
            label="Alter",
            placeholder="Wie alt bist du?",
            required=True,
            max_length=3
        )

        self.erfahrung = discord.ui.TextInput(
            label="Erfahrung",
            placeholder=vorlage["erfahrung"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
            default=(
                vorlage["auto_erfahrung"]
                if auto_fill
                else ""
            )
        )

        self.motivation = discord.ui.TextInput(
            label="Motivation",
            placeholder=vorlage["motivation"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
            default=(
                vorlage["auto_motivation"]
                if auto_fill
                else ""
            )
        )

        self.zusatz = discord.ui.TextInput(
            label="Zusatzfrage",
            placeholder=vorlage["zusatz"],
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
            default=(
                vorlage["auto_zusatz"]
                if auto_fill
                else ""
            )
        )

        self.add_item(self.name)

        self.add_item(self.alter)

        self.add_item(self.erfahrung)

        self.add_item(self.motivation)

        self.add_item(self.zusatz)


    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not BOT_AKTIV and not is_owner(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "🔴 Der Bot ist momentan ausgeschaltet.",
                ephemeral=True
            )

            return

        if (
            WARTUNG_AKTIV
            and not is_owner(
                interaction.user.id
            )
        ):

            await interaction.response.send_message(
                "🛠️ Der Bot befindet sich momentan "
                "im Wartungsmodus.",
                ephemeral=True
            )

            return

        channel = bot.get_channel(
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
                f"{interaction.user} → {self.rolle}"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, "
                "im Bewerbungs-Channel zu schreiben.",
                ephemeral=True
            )

        except Exception as error:

            print(
                f"❌ Fehler beim Senden der Bewerbung: {error}"
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "❌ Beim Absenden ist ein Fehler aufgetreten.",
                    ephemeral=True
                )


# =========================================================
# MODUS-AUSWAHL
# =========================================================

class ModusAuswahl(
    discord.ui.Select
):

    def __init__(
        self,
        rolle: str
    ):

        self.rolle = rolle

        options = [

            discord.SelectOption(
                label="Automatisch ausfüllen",
                value="auto",
                description=(
                    "Antworten werden vorausgefüllt"
                ),
                emoji="🚀"
            ),

            discord.SelectOption(
                label="Manuell ausfüllen",
                value="manuell",
                description=(
                    "Alle Felder selbst ausfüllen"
                ),
                emoji="✏️"
            )
        ]

        super().__init__(
            placeholder=(
                "📝 Wie möchtest du das Formular ausfüllen?"
            ),
            min_values=1,
            max_values=1,
            options=options
        )


    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not BOT_AKTIV and not is_owner(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "🔴 Der Bot ist momentan ausgeschaltet.",
                ephemeral=True
            )

            return

        if (
            WARTUNG_AKTIV
            and not is_owner(
                interaction.user.id
            )
        ):

            await interaction.response.send_message(
                "🛠️ Der Bot befindet sich momentan "
                "im Wartungsmodus.",
                ephemeral=True
            )

            return

        auto_fill = (
            self.values[0] == "auto"
        )

        modal = BewerbungModal(
            rolle=self.rolle,
            auto_fill=auto_fill
        )

        if auto_fill:

            modal.name.default = str(
                interaction.user
            )

        await interaction.response.send_modal(
            modal
        )


# =========================================================
# MODUS VIEW
# =========================================================

class ModusView(
    discord.ui.View
):

    def __init__(
        self,
        rolle: str
    ):

        super().__init__(
            timeout=60
        )

        self.add_item(
            ModusAuswahl(rolle)
        )


# =========================================================
# BEWERBUNGS SELECT
# =========================================================

class AutomatischesFormular(
    discord.ui.Select
):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Admin",
                value="Admin",
                description=(
                    "Bewerbung für das Admin-Team"
                ),
                emoji="👑"
            ),

            discord.SelectOption(
                label="Moderator",
                value="Moderator",
                description=(
                    "Bewerbung für das Moderationsteam"
                ),
                emoji="🛡️"
            ),

            discord.SelectOption(
                label="Supporter",
                value="Supporter",
                description=(
                    "Bewerbung für das Support-Team"
                ),
                emoji="💬"
            ),

            discord.SelectOption(
                label="Entwickler",
                value="Entwickler",
                description=(
                    "Bewerbung als Entwickler"
                ),
                emoji="💻"
            )
        ]

        super().__init__(
            placeholder="📋 Wähle deine Bewerbung...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="bewerbung_rolle_select"
        )


    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not BOT_AKTIV and not is_owner(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "🔴 Der Bot ist momentan ausgeschaltet.",
                ephemeral=True
            )

            return

        if (
            WARTUNG_AKTIV
            and not is_owner(
                interaction.user.id
            )
        ):

            await interaction.response.send_message(
                "🛠️ Der Bot befindet sich momentan "
                "im Wartungsmodus.",
                ephemeral=True
            )

            return

        rolle = self.values[0]

        await interaction.response.send_message(
            "Möchtest du das Formular automatisch "
            "oder manuell ausfüllen?",
            view=ModusView(rolle),
            ephemeral=True
        )


# =========================================================
# BEWERBUNG VIEW
# =========================================================

class BewerbungView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            AutomatischesFormular()
        )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    global view_registered

    print("")

    print("===================================")

    print("🤖 BOT ONLINE")

    print(
        f"👤 Eingeloggt als: {bot.user}"
    )

    if bot.user:

        print(
            f"🆔 Bot-ID: {bot.user.id}"
        )

    print(
        f"📡 Ping: {round(bot.latency * 1000)} ms"
    )

    print(
        "🔌 Bot-Aktiv: "
        + (
            "JA"
            if BOT_AKTIV
            else "NEIN"
        )
    )

    print(
        "🛠️ Wartungsmodus: "
        + (
            "AKTIV"
            if WARTUNG_AKTIV
            else "INAKTIV"
        )
    )

    print("===================================")

    print("")

    if not view_registered:

        bot.add_view(
            BewerbungView()
        )

        view_registered = True

        print(
            "✅ Bewerbung-View registriert."
        )

    try:

        synced = await tree.sync()

        print(
            f"✅ {len(synced)} Slash Commands synchronisiert."
        )

    except Exception as error:

        print(
            f"❌ Fehler beim Synchronisieren: {error}"
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
        "🔄 discord.py versucht automatisch "
        "wieder zu verbinden."
    )


# =========================================================
# RESUMED
# =========================================================

@bot.event
async def on_resumed():

    print(
        "✅ Discord-Verbindung wiederhergestellt."
    )

    print(
        f"📡 Ping: {round(bot.latency * 1000)} ms"
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
                    f"Ping: {round(bot.latency * 1000)} ms | "
                    "Aktiv: "
                    + (
                        "AN"
                        if BOT_AKTIV
                        else "AUS"
                    )
                    + " | Wartung: "
                    + (
                        "AN"
                        if WARTUNG_AKTIV
                        else "AUS"
                    )
                )

            else:

                print(
                    "⚠️ Watchdog: Bot momentan nicht bereit."
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

    if not BOT_AKTIV and not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "🔴 Der Bot ist momentan ausgeschaltet.",
            ephemeral=True
        )

        return

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 Pong!\n📡 Ping: **{latency} ms**"
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

    if not BOT_AKTIV and not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "🔴 Das Bewerbungssystem ist momentan deaktiviert.",
            ephemeral=True
        )

        return

    if (
        WARTUNG_AKTIV
        and not is_owner(
            interaction.user.id
        )
    ):

        await interaction.response.send_message(
            "🛠️ Der Bot befindet sich momentan "
            "im Wartungsmodus.",
            ephemeral=True
        )

        return

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
# /BOT GROUP
# =========================================================

bot_group = discord.app_commands.Group(
    name="bot",
    description="Bot-Verwaltung"
)


# =========================================================
# /BOT AN
# =========================================================

@bot_group.command(
    name="an",
    description="Schaltet den Bot ein."
)
async def bot_an(
    interaction: discord.Interaction
):

    global BOT_AKTIV

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    BOT_AKTIV = True

    await interaction.response.send_message(
        "🟢 **Bot wurde eingeschaltet.**\n\n"
        "Der Bot ist wieder aktiv."
    )

    print(
        "🟢 Bot-Aktivstatus: AN"
    )


# =========================================================
# /BOT AUS
# =========================================================

@bot_group.command(
    name="aus",
    description="Schaltet die normalen Bot-Funktionen aus."
)
async def bot_aus(
    interaction: discord.Interaction
):

    global BOT_AKTIV

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    BOT_AKTIV = False

    await interaction.response.send_message(
        "🔴 **Bot wurde ausgeschaltet.**\n\n"
        "Die Discord-Verbindung bleibt bestehen, "
        "aber normale Bot-Funktionen sind deaktiviert.\n\n"
        "Mit `/bot an` kannst du ihn wieder aktivieren."
    )

    print(
        "🔴 Bot-Aktivstatus: AUS"
    )


# =========================================================
# /BOT STATUS
# =========================================================

@bot_group.command(
    name="status",
    description="Zeigt den aktuellen Bot-Status."
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

    if not BOT_AKTIV:

        status_text = (
            "🔴 Ausgeschaltet"
        )

        status_color = (
            discord.Color.red()
        )

    elif WARTUNG_AKTIV:

        status_text = (
            "🟡 Wartungsmodus"
        )

        status_color = (
            discord.Color.orange()
        )

    else:

        status_text = (
            "🟢 Online und aktiv"
        )

        status_color = (
            discord.Color.green()
        )

    embed = discord.Embed(
        title="🤖 Bot Status",
        color=status_color,
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="Bot",
        value=status_text,
        inline=False
    )

    embed.add_field(
        name="Discord",
        value=(
            "🟢 Verbunden"
            if bot.is_ready()
            else "🔴 Getrennt"
        ),
        inline=True
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

    embed.add_field(
        name="Wartung",
        value=(
            "🟡 Aktiv"
            if WARTUNG_AKTIV
            else "🟢 Inaktiv"
        ),
        inline=True
    )

    if bot.guilds:

        embed.add_field(
            name="Mitglieder",
            value=str(
                bot.guilds[0].member_count
            ),
            inline=True
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# /BOT WARTUNG
# =========================================================

@bot_group.command(
    name="wartung",
    description="Steuert den Wartungsmodus."
)
@discord.app_commands.describe(
    modus="Wartungsmodus"
)
@discord.app_commands.choices(
    modus=[

        discord.app_commands.Choice(
            name="🛠️ Einschalten",
            value="on"
        ),

        discord.app_commands.Choice(
            name="✅ Ausschalten",
            value="off"
        ),

        discord.app_commands.Choice(
            name="📊 Status",
            value="status"
        ),

        discord.app_commands.Choice(
            name="👥 Mitglieder",
            value="member"
        )
    ]
)
async def bot_wartung(
    interaction: discord.Interaction,
    modus: discord.app_commands.Choice[str]
):

    global WARTUNG_AKTIV
    global WARTUNGS_GRUND

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    if modus.value == "on":

        WARTUNG_AKTIV = True

        await interaction.response.send_message(
            "🛠️ **Wartungsmodus AKTIVIERT**",
            ephemeral=True
        )

        await sende_wartungs_ankuendigung(
            interaction,
            aktiv=True
        )

        print(
            "🛠️ Wartungsmodus AKTIVIERT"
        )

    elif modus.value == "off":

        WARTUNG_AKTIV = False

        await interaction.response.send_message(
            "✅ **Wartungsmodus DEAKTIVIERT**",
            ephemeral=True
        )

        await sende_wartungs_ankuendigung(
            interaction,
            aktiv=False
        )

        print(
            "✅ Wartungsmodus DEAKTIVIERT"
        )

    elif modus.value == "status":

        status = (
            "🛠️ AKTIV"
            if WARTUNG_AKTIV
            else "✅ INAKTIV"
        )

        embed = discord.Embed(
            title="📊 Wartungsmodus-Status",
            color=(
                discord.Color.orange()
                if WARTUNG_AKTIV
                else discord.Color.green()
            )
        )

        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )

        embed.add_field(
            name="Grund",
            value=WARTUNGS_GRUND,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    elif modus.value == "member":

        if not bot.guilds:

            await interaction.response.send_message(
                "❌ Keine Server-Informationen verfügbar.",
                ephemeral=True
            )

            return

        guild = bot.guilds[0]

        total = guild.member_count or 0

        bots_count = sum(
            1
            for member in guild.members
            if member.bot
        )

        humans = total - bots_count

        online = sum(
            1
            for member in guild.members
            if member.status != discord.Status.offline
        )

        offline = total - online

        embed = discord.Embed(
            title="👥 Server-Mitglieder",
            description=f"**Server:** {guild.name}",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="📊 Gesamt",
            value=f"**{total}**",
            inline=False
        )

        embed.add_field(
            name="👤 Menschen",
            value=str(humans),
            inline=True
        )

        embed.add_field(
            name="🤖 Bots",
            value=str(bots_count),
            inline=True
        )

        embed.add_field(
            name="🟢 Online",
            value=str(online),
            inline=True
        )

        embed.add_field(
            name="⚫ Offline",
            value=str(offline),
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
# RENDER RESTART VIEW
# =========================================================

class RestartView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=60
        )


    @discord.ui.button(
        label="Server neu starten",
        emoji="🔄",
        style=discord.ButtonStyle.danger
    )
    async def restart_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_owner(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "❌ Du darfst den Server nicht neu starten.",
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

        button.disabled = True

        await interaction.response.edit_message(
            content=(
                "🔄 **Render-Service wird neu gestartet...**\n\n"
                "⏳ Bitte kurz warten."
            ),
            view=self
        )

        url = (
            "https://api.render.com/v1/services/"
            f"{RENDER_SERVICE_ID}/restart"
        )

        headers = {
            "Authorization": (
                f"Bearer {RENDER_API_KEY}"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        print("")

        print(
            "==================================="
        )

        print(
            "🔄 RENDER RESTART"
        )

        print(
            "==================================="
        )

        print(
            f"🆔 Service-ID: {RENDER_SERVICE_ID}"
        )

        print(
            "⏳ Sende Restart-Anfrage..."
        )

        try:

            response = await asyncio.to_thread(
                requests.post,
                url,
                headers=headers,
                timeout=20
            )

            print(
                f"📡 HTTP Status: "
                f"{response.status_code}"
            )

            print(
                f"📨 Render Antwort: "
                f"{response.text}"
            )

            print(
                "==================================="
            )

            if response.status_code in (
                200,
                201,
                202,
                204
            ):

                print(
                    "✅ Render Restart erfolgreich ausgelöst."
                )

                try:

                    await interaction.edit_original_response(
                        content=(
                            "✅ **Render-Neustart ausgelöst!**\n\n"
                            "🔄 Render startet den Service neu.\n"
                            "📡 Der Bot verbindet sich danach "
                            "automatisch wieder mit Discord."
                        ),
                        view=self
                    )

                except Exception as error:

                    print(
                        "ℹ️ Discord-Nachricht konnte "
                        f"nicht mehr geändert werden: {error}"
                    )

            else:

                print(
                    "❌ Render Restart fehlgeschlagen."
                )

                button.disabled = False

                await interaction.edit_original_response(
                    content=(
                        "❌ **Render-Neustart fehlgeschlagen.**\n\n"
                        f"HTTP Status: "
                        f"`{response.status_code}`\n"
                        f"Antwort: "
                        f"`{response.text[:1000]}`"
                    ),
                    view=self
                )

        except requests.RequestException as error:

            print(
                f"❌ Render API Fehler: {error}"
            )

            button.disabled = False

            await interaction.edit_original_response(
                content=(
                    "❌ **Fehler bei der Render-API.**\n\n"
                    f"`{error}`"
                ),
                view=self
            )


# =========================================================
# /RESTART
# =========================================================

@tree.command(
    name="restart",
    description="Zeigt den Server-Restart-Button."
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

    embed = discord.Embed(
        title="🔄 Server Neustart",
        description=(
            "Mit dem Button kannst du den "
            "Render-Service neu starten.\n\n"
            "⚠️ Der Service wird dabei neu gestartet."
        ),
        color=discord.Color.orange()
    )

    await interaction.response.send_message(
        embed=embed,
        view=RestartView(),
        ephemeral=True
    )


# =========================================================
# /WARTUNG
# =========================================================

@tree.command(
    name="wartung",
    description="Steuert den Wartungsmodus."
)
@discord.app_commands.describe(
    modus="Wartungsmodus"
)
@discord.app_commands.choices(
    modus=[

        discord.app_commands.Choice(
            name="🛠️ Einschalten",
            value="on"
        ),

        discord.app_commands.Choice(
            name="✅ Ausschalten",
            value="off"
        ),

        discord.app_commands.Choice(
            name="📊 Status",
            value="status"
        ),

        discord.app_commands.Choice(
            name="👥 Mitglieder",
            value="member"
        )
    ]
)
async def wartung(
    interaction: discord.Interaction,
    modus: discord.app_commands.Choice[str]
):

    global WARTUNG_AKTIV
    global WARTUNGS_GRUND

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    if modus.value == "on":

        WARTUNG_AKTIV = True

        await interaction.response.send_message(
            "🛠️ **Wartungsmodus AKTIVIERT**",
            ephemeral=True
        )

        await sende_wartungs_ankuendigung(
            interaction,
            aktiv=True
        )

        print(
            "🛠️ Wartungsmodus AKTIVIERT"
        )

    elif modus.value == "off":

        WARTUNG_AKTIV = False

        await interaction.response.send_message(
            "✅ **Wartungsmodus DEAKTIVIERT**",
            ephemeral=True
        )

        await sende_wartungs_ankuendigung(
            interaction,
            aktiv=False
        )

        print(
            "✅ Wartungsmodus DEAKTIVIERT"
        )

    elif modus.value == "status":

        status = (
            "🛠️ AKTIV"
            if WARTUNG_AKTIV
            else "✅ INAKTIV"
        )

        embed = discord.Embed(
            title="📊 Wartungsmodus-Status",
            color=(
                discord.Color.orange()
                if WARTUNG_AKTIV
                else discord.Color.green()
            )
        )

        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )

        embed.add_field(
            name="Grund",
            value=WARTUNGS_GRUND,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    elif modus.value == "member":

        if not bot.guilds:

            await interaction.response.send_message(
                "❌ Keine Server-Informationen verfügbar.",
                ephemeral=True
            )

            return

        guild = bot.guilds[0]

        total = guild.member_count or 0

        bots_count = sum(
            1
            for member in guild.members
            if member.bot
        )

        humans = total - bots_count

        online = sum(
            1
            for member in guild.members
            if member.status != discord.Status.offline
        )

        offline = total - online

        embed = discord.Embed(
            title="👥 Server-Mitglieder",
            description=f"**Server:** {guild.name}",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="📊 Gesamt",
            value=f"**{total}**",
            inline=False
        )

        embed.add_field(
            name="👤 Menschen",
            value=str(humans),
            inline=True
        )

        embed.add_field(
            name="🤖 Bots",
            value=str(bots_count),
            inline=True
        )

        embed.add_field(
            name="🟢 Online",
            value=str(online),
            inline=True
        )

        embed.add_field(
            name="⚫ Offline",
            value=str(offline),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# =========================================================
# ERROR HANDLER
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

    print(
        "==================================="
    )

    print(
        "🚀 Starte Discord Bot..."
    )

    print(
        "==================================="
    )

    print("")

    try:

        bot.run(
            TOKEN
        )

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
