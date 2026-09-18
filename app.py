import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# =========================
# BEWERBUNGS-PANEL
# =========================

class BewerbungView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🛡️ Supporter",
        style=discord.ButtonStyle.secondary,
        custom_id="bewerbung_supporter"
    )
    async def supporter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🛡️ **Supporter Bewerbung**\n\nBitte beschreibe deine Erfahrung und warum du Supporter werden möchtest.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🛡️ Moderator",
        style=discord.ButtonStyle.primary,
        custom_id="bewerbung_moderator"
    )
    async def moderator(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🛡️ **Moderator Bewerbung**\n\nBitte beschreibe deine Erfahrung und warum du Moderator werden möchtest.",
            ephemeral=True
        )

    @discord.ui.button(
        label="👨‍💻 Entwickler",
        style=discord.ButtonStyle.success,
        custom_id="bewerbung_entwickler"
    )
    async def entwickler(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "👨‍💻 **Entwickler Bewerbung**\n\nBitte beschreibe deine Programmiererfahrung.",
            ephemeral=True
        )

    @discord.ui.button(
        label="👑 Admin",
        style=discord.ButtonStyle.danger,
        custom_id="bewerbung_admin"
    )
    async def admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "👑 **Admin Bewerbung**\n\nBitte beschreibe deine Erfahrung im Bereich Moderation/Administration.",
            ephemeral=True
        )


# =========================
# SLASH COMMAND
# =========================

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
        "✅ Bewerbungs-Panel erstellt!",
        ephemeral=True
    )


# =========================
# BOT START
# =========================

@bot.event
async def on_ready():
    bot.add_view(BewerbungView())

    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} Slash Commands synchronisiert.")
    except Exception as e:
        print(f"❌ Fehler: {e}")

    print(f"🤖 Online als {bot.user}")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt!")

bot.run(TOKEN)
