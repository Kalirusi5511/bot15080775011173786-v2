# app1.py
import logging
import discord
from discord.ext import commands
from discord import app_commands

import config
from app2 import AutoFillModal, ManualModal

log = logging.getLogger("bewerbung")


# ============================================================
# AUSWAHL-VIEW (erscheint NACH Klick auf "Bewerben")
# ============================================================

class AuswahlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(
        label="Auto-Fill",
        style=discord.ButtonStyle.success,
        emoji="⚡",
        custom_id="wahl_auto"
    )
    async def auto_fill(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(AutoFillModal(interaction.user))
        except Exception as e:
            log.exception(f"Auto-Modal-Fehler: {e}")

    @discord.ui.button(
        label="Manuell",
        style=discord.ButtonStyle.primary,
        emoji="✍️",
        custom_id="wahl_manuell"
    )
    async def manuell(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(ManualModal(interaction.user))
        except Exception as e:
            log.exception(f"Manuell-Modal-Fehler: {e}")


# ============================================================
# HAUP T-VIEW (Button im Bewerbungs-Embed)
# ============================================================

class BewerbungView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        style=discord.ButtonStyle.green,
        emoji="📩",
        custom_id="bewerbung_button"
    )
    async def bewerben(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not config.BOT_AKTIV:
            await interaction.response.send_message(
                "🔴 Der Bot ist deaktiviert.", ephemeral=True
            )
            return

        if config.MAINTENANCE_MODE:
            await interaction.response.send_message(
                "🛠️ Wartungsmodus aktiv.", ephemeral=True
            )
            return

        if interaction.user.id in config.BLOCKLIST:
            await interaction.response.send_message(
                "❌ Du bist gesperrt.", ephemeral=True
            )
            return

        # Auswahl-Menü anzeigen
        await interaction.response.send_message(
            "**Wie möchtest du das Formular ausfüllen?**\n"
            "⚡ **Auto-Fill** – Name & Datum werden vorausgefüllt\n"
            "✍️ **Manuell** – alle Felder selbst ausfüllen",
            view=AuswahlView(),
            ephemeral=True
        )


# ============================================================
# COG
# ============================================================

class BewerbungCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(BewerbungView())

    @app_commands.command(name="bewerbung", description="Öffnet das Bewerbungsformular.")
    async def bewerbung(self, interaction: discord.Interaction):

        if not config.BOT_AKTIV:
            await interaction.response.send_message(
                "🔴 Der Bot ist deaktiviert.", ephemeral=True
            )
            return

        if config.MAINTENANCE_MODE:
            await interaction.response.send_message(
                "🛠️ Wartungsmodus aktiv.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📩 Bewerbung",
            description=(
                "Klicke auf den Button unten, um eine Bewerbung zu starten.\n\n"
                "Du kannst wählen zwischen:\n"
                "⚡ **Auto-Fill** (Name & Datum vorausgefüllt)\n"
                "✍️ **Manuell** (alles selbst ausfüllen)"
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            view=BewerbungView()
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BewerbungCog(bot))