# app2.py
import logging
import discord
import config

log = logging.getLogger("bewerbung_modes")


# ============================================================
# MODAL 1: AUTO-FILL
# ============================================================

class AutoFillModal(discord.ui.Modal, title="📩 Bewerbung (Auto)"):

    def __init__(self, user: discord.User):
        super().__init__()
        self.user = user

        # ---- AUTO-FILL ----
        self.name = discord.ui.TextInput(
            label="Name",
            default=user.display_name,
            required=True,
            max_length=100
        )
        self.datum = discord.ui.TextInput(
            label="Datum",
            default=discord.utils.utcnow().strftime("%d.%m.%Y"),
            required=True,
            max_length=15
        )
        self.alter = discord.ui.TextInput(
            label="Alter",
            placeholder="Wie alt bist du?",
            required=True,
            max_length=3
        )
        self.erfahrung = discord.ui.TextInput(
            label="Erfahrung",
            style=discord.TextStyle.paragraph,
            placeholder="Erzähle etwas über deine Erfahrung.",
            required=True,
            max_length=1000
        )
        self.motivation = discord.ui.TextInput(
            label="Motivation",
            style=discord.TextStyle.paragraph,
            placeholder="Warum möchtest du dich bewerben?",
            required=True,
            max_length=1000
        )

        for item in (self.name, self.datum, self.alter,
                     self.erfahrung, self.motivation):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await send_bewerbung(
            interaction,
            interaction.user,
            self.name.value,
            self.datum.value,
            self.alter.value,
            self.erfahrung.value,
            self.motivation.value,
            mode="Auto-Fill"
        )


# ============================================================
# MODAL 2: MANUELL
# ============================================================

class ManualModal(discord.ui.Modal, title="📩 Bewerbung (Manuell)"):

    def __init__(self, user: discord.User):
        super().__init__()
        self.user = user

        # ---- ALLES LEER ----
        self.name = discord.ui.TextInput(
            label="Name",
            placeholder="Dein Name",
            required=True,
            max_length=100
        )
        self.datum = discord.ui.TextInput(
            label="Datum",
            placeholder="TT.MM.JJJJ",
            required=True,
            max_length=15
        )
        self.alter = discord.ui.TextInput(
            label="Alter",
            placeholder="Wie alt bist du?",
            required=True,
            max_length=3
        )
        self.erfahrung = discord.ui.TextInput(
            label="Erfahrung",
            style=discord.TextStyle.paragraph,
            placeholder="Erzähle etwas über deine Erfahrung.",
            required=True,
            max_length=1000
        )
        self.motivation = discord.ui.TextInput(
            label="Motivation",
            style=discord.TextStyle.paragraph,
            placeholder="Warum möchtest du dich bewerben?",
            required=True,
            max_length=1000
        )

        for item in (self.name, self.datum, self.alter,
                     self.erfahrung, self.motivation):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await send_bewerbung(
            interaction,
            interaction.user,
            self.name.value,
            self.datum.value,
            self.alter.value,
            self.erfahrung.value,
            self.motivation.value,
            mode="Manuell"
        )


# ============================================================
# GEMEINSAME SENDEFUNKTION
# ============================================================

async def send_bewerbung(
    interaction: discord.Interaction,
    user: discord.User,
    name: str,
    datum: str,
    alter: str,
    erfahrung: str,
    motivation: str,
    mode: str = "Unbekannt"
):

    # sofort defer → verhindert Timeout
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.InteractionResponded:
        pass
    except Exception as e:
        log.error(f"Defer fehlgeschlagen: {e}")
        return

    embed = discord.Embed(
        title="📩 Neue Bewerbung",
        description=f"**Modus:** {mode}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(
        name="👤 Bewerber",
        value=f"{user.mention}\n`{user.id}`",
        inline=False
    )
    embed.add_field(name="📛 Name", value=name, inline=True)
    embed.add_field(name="📅 Datum", value=datum, inline=True)
    embed.add_field(name="🎂 Alter", value=alter, inline=True)
    embed.add_field(name="💼 Erfahrung", value=erfahrung, inline=False)
    embed.add_field(name="💡 Motivation", value=motivation, inline=False)

    channel = interaction.client.get_channel(config.BEWERBUNGS_CHANNEL_ID)

    if channel is None:
        await interaction.followup.send(
            "❌ Bewerbungs-Channel nicht gefunden.",
            ephemeral=True
        )
        log.error("Bewerbungs-Channel nicht gefunden.")
        return

    try:
        await channel.send(embed=embed)
        await interaction.followup.send(
            "✅ Deine Bewerbung wurde abgeschickt.",
            ephemeral=True
        )
        log.info(f"📩 Bewerbung ({mode}) von {user}")
    except discord.HTTPException as e:
        await interaction.followup.send(
            "❌ Senden fehlgeschlagen.",
            ephemeral=True
        )
        log.error(f"Bewerbungsfehler: {e}")