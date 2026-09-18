import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# Render Webserver
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot läuft! ✅"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()


# Discord Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class BewerbungView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🛡️ Supporter",
        style=discord.ButtonStyle.secondary,
        custom_id="bewerbung_supporter"
    )
    async def supporter(self, interaction, button):
        await interaction.response.send_message(
            "🛡️ **Supporter Bewerbung**\nBitte beschreibe deine Erfahrung.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🛡️ Moderator",
        style=discord.ButtonStyle.primary,
        custom_id="bewerbung_moderator"
    )
    async def moderator(self, interaction, button):
        await interaction.response.send_message(
            "🛡️ **Moderator Bewerbung**\nBitte beschreibe deine Erfahrung.",
            ephemeral=True
        )

    @discord.ui.button(
        label="👨‍💻 Entwickler",
        style=discord.ButtonStyle.success,
        custom_id="bewerbung_entwickler"
    )
    async def entwickler(self, interaction, button):
        await interaction.response.send_message(
            "👨‍💻 **Entwickler Bewerbung**\nBitte beschreibe deine Programmiererfahrung.",
            ephemeral=True
        )

    @discord.ui.button(
        label="👑 Admin",
        style=discord.ButtonStyle.danger,
        custom_id="bewerbung_admin"
    )
    async def admin(self, interaction, button):
        await interaction.response.send_message(
            "👑 **Admin Bewerbung**\nBitte beschreibe deine Erfahrung.",
            ephemeral=True
        )


@bot.tree.command(
    name="bewerbung",
    description="Erstellt das Bewerbungs-System."
)
async def bewerbung(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🎓 Bewerbungs System",
        description=(
            "Willkommen zum Bewerbungs-System.\n"
            "🛡️ Supporter\n"
            "🛡️ Moderator\n"
            "👨‍💻 Entwickler\n"
            "👑 Admin\n\n"
            "Klicke auf einen Button."
        ),
        color=discord.Color.blurple()
    )

    embed.timestamp = discord.utils.utcnow()

    await interaction.channel.send(
        embed=embed,
        view=BewerbungView()
    )

    await interaction.response.send_message(
        "✅ Panel erstellt!",
        ephemeral=True
    )


@bot.event
async def on_ready():
    bot.add_view(BewerbungView())

    try:
        await bot.tree.sync()
        print("✅ Slash Commands synchronisiert!")
    except Exception as e:
        print(f"❌ Sync Fehler: {e}")

    print(f"🤖 Online: {bot.user}")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt!")

bot.run(TOKEN)
