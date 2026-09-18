import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# =========================
# RENDER WEB SERVER
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot läuft! ✅"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()


# =========================
# DISCORD BOT
# =========================

intents = discord.Intents.default()
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# BEWERBUNGS-FORMULAR
# =========================

class BewerbungModal(discord.ui.Modal):

    def __init__(self, rolle):
        super().__init__(title=f"{rolle} Bewerbung")
        self.rolle = rolle

        self.alter = discord.ui.TextInput(
            label="Wie alt bist du?",
            placeholder="z.B. 16",
            required=True,
            max_length=3
        )

        self.erfahrung = discord.ui.TextInput(
            label="Deine Erfahrung",
            placeholder="Erzähle uns von deiner Erfahrung...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.motivation = discord.ui.TextInput(
            label="Warum möchtest du die Rolle?",
            placeholder="Warum möchtest du Teil des Teams werden?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.staerken = discord.ui.TextInput(
            label="Deine Stärken",
            placeholder="z.B. freundlich, geduldig, zuverlässig...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )

        self.zusatz = discord.ui.TextInput(
            label="Zusätzliche Informationen",
            placeholder="Optional weitere Informationen...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )

        self.add_item(self.alter)
        self.add_item(self.erfahrung)
        self.add_item(self.motivation)
        self.add_item(self.staerken)
        self.add_item(self.zusatz)

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title=f"📝 Neue {self.rolle} Bewerbung",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=f"{interaction.user.mention}\n`{interaction.user}`",
            inline=False
        )

        embed.add_field(
            name="🎯 Gewünschte Rolle",
            value=self.rolle,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.alter.value,
            inline=True
        )

        embed.add_field(
            name="💼 Erfahrung",
            value=self.erfahrung.value,
            inline=False
        )

        embed.add_field(
            name="🎯 Motivation",
            value=self.motivation.value,
            inline=False
        )

        embed.add_field(
            name="💪 Stärken",
            value=self.staerken.value,
            inline=False
        )

        if self.zusatz.value:
            embed.add_field(
                name="📌 Zusatz",
                value=self.zusatz.value,
                inline=False
            )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        # Bewerbungskanal aus Environment Variable
        channel_id = os.getenv("BEWERBUNGS_CHANNEL_ID")

        if channel_id:
            channel = interaction.guild.get_channel(int(channel_id))

            if channel:
                await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich abgeschickt!",
            ephemeral=True
        )


# =========================
# BUTTONS
# =========================

class BewerbungView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🛡️ Supporter",
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
        label="🛡️ Moderator",
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
        label="👨‍💻 Entwickler",
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
        label="👑 Admin",
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


# =========================
# /BEWERBUNG
# =========================

@bot.tree.command(
    name="bewerbung",
    description="Erstellt das Bewerbungs-System."
)
async def bewerbung(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🎓 Bewerbungs System",
        description=(
            "Willkommen zum Bewerbungs-System.\n\n"
            "🛡️ **Supporter**\n"
            "🛡️ **Moderator**\n"
            "👨‍💻 **Entwickler**\n"
            "👑 **Admin**\n\n"
            "Klicke auf einen Button, um dich zu bewerben."
        ),
        color=discord.Color.blurple()
    )

    embed.timestamp = discord.utils.utcnow()

    await interaction.channel.send(
        embed=embed,
        view=BewerbungView()
    )

    await interaction.response.send_message(
        "✅ Bewerbungs-Panel erstellt!",
        ephemeral=True
    )


# =========================
# START
# =========================

@bot.event
async def on_ready():

    bot.add_view(BewerbungView())

    try:
        await bot.tree.sync()
        print("✅ Slash Commands synchronisiert!")
    except Exception as e:
        print(f"❌ Sync Fehler: {e}")

    print(f"🤖 Online als {bot.user}")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt!")

bot.run(TOKEN)
