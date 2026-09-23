# owner_check.py
import logging
import discord
from discord.ext import commands
from discord import app_commands

import config

log = logging.getLogger("owner_check")


def has_required_role(member: discord.Member) -> bool:
    """Prüft, ob der User 'Owner 2' oder 'Admin Rang' hat."""
    if not isinstance(member, discord.Member):
        return False

    role_names = [r.name for r in member.roles]

    return (
        config.ROLE_OWNER in role_names
        or config.ROLE_ADMIN in role_names
    )


# ---- Gruppe ----
owner_group = app_commands.Group(
    name="owner",
    description="Owner-Verwaltung (max. 4)"
)


@owner_group.command(
    name="ich",
    description="Setzt dich als Owner (nur mit Owner 2 oder Admin Rang)."
)
async def owner_ich(interaction: discord.Interaction):

    # 1. Rollen-Prüfung
    if not has_required_role(interaction.user):
        await interaction.response.send_message(
            f"❌ Du benötigst die Rolle **{config.ROLE_OWNER}** "
            f"oder **{config.ROLE_ADMIN}**.",
            ephemeral=True
        )
        return

    # 2. Bereits Owner?
    if config.OWNERS:
        await interaction.response.send_message(
            "❌ Owner sind bereits gesetzt. Nutze `/owner add`.",
            ephemeral=True
        )
        return

    # 3. Setzen
    if config.add_owner(interaction.user.id):
        log.info(f"👑 Neuer Owner: {interaction.user} ({interaction.user.id})")
        await interaction.response.send_message(
            f"👑 Du wurdest als Owner gesetzt: `{interaction.user.id}`\n"
            f"Nutze `/owner add`, um weitere Owner hinzuzufügen.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Konnte dich nicht als Owner setzen.",
            ephemeral=True
        )


@owner_group.command(
    name="add",
    description="Fügt einen weiteren Owner hinzu (max. 4)."
)
@app_commands.describe(user="Der User, der Owner werden soll")
async def owner_add(interaction: discord.Interaction, user: discord.User):

    if not config.is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ Keine Berechtigung.", ephemeral=True
        )
        return

    if len(config.OWNERS) >= config.MAX_OWNERS:
        await interaction.response.send_message(
            f"❌ Maximal {config.MAX_OWNERS} Owner erlaubt.",
            ephemeral=True
        )
        return

    if config.add_owner(user.id):
        log.info(f"👑 Owner hinzugefügt: {user} ({user.id})")
        await interaction.response.send_message(
            f"✅ {user.mention} ist jetzt Owner.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {user.mention} ist bereits Owner.",
            ephemeral=True
        )


@owner_group.command(
    name="remove",
    description="Entfernt einen Owner."
)
@app_commands.describe(user="Der User, der entfernt werden soll")
async def owner_remove(interaction: discord.Interaction, user: discord.User):

    if not config.is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ Keine Berechtigung.", ephemeral=True
        )
        return

    if user.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Du kannst dich nicht selbst entfernen.",
            ephemeral=True
        )
        return

    if config.remove_owner(user.id):
        log.info(f"🚫 Owner entfernt: {user} ({user.id})")
        await interaction.response.send_message(
            f"✅ {user.mention} ist kein Owner mehr.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {user.mention} ist kein Owner.",
            ephemeral=True
        )


@owner_group.command(
    name="list",
    description="Zeigt alle Owner."
)
async def owner_list(interaction: discord.Interaction):

    if not config.OWNERS:
        await interaction.response.send_message(
            "📭 Noch keine Owner gesetzt.",
            ephemeral=True
        )
        return

    text = "\n".join(
        f"• <@{uid}> (`{uid}`)"
        for uid in config.OWNERS
    )

    await interaction.response.send_message(
        f"👑 **Owner ({len(config.OWNERS)}/{config.MAX_OWNERS})**\n\n{text}",
        ephemeral=True
    )


# ---- Cog ----
class OwnerCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(owner_group)


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCog(bot))