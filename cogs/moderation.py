"""
Moderation Commands — Both prefix (!) and slash (/) commands.
Slash commands give the interactive Discord UI with parameter prompts.
Prefix commands work as a text-based fallback.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import re


class Moderation(commands.Cog):
    """Moderation commands — slash + prefix."""

    def __init__(self, bot):
        self.bot = bot

    # ══════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════

    def _parse_duration(self, text):
        text = text.strip().lower()
        match = re.match(r'^(\d+)\s*([smhd])?$', text)
        if not match: return None
        amount = int(match.group(1))
        unit = match.group(2) or 'm'
        if unit == 's': return timedelta(seconds=amount)
        if unit == 'm': return timedelta(minutes=amount)
        if unit == 'h': return timedelta(hours=amount)
        if unit == 'd': return timedelta(days=min(amount, 28))
        return None

    def _fmt(self, td):
        total = int(td.total_seconds())
        if total < 60: return f"{total} second(s)"
        if total < 3600: return f"{total // 60} minute(s)"
        if total < 86400: return f"{total // 3600} hour(s)"
        return f"{total // 86400} day(s)"

    def _perm_error(self, member, action):
        return discord.Embed(
            title="❌ Missing Permissions",
            description=f"I don't have permission to **{action}** {member.mention}. "
                        "Make sure my role is higher than theirs.",
            color=discord.Color.red()
        )

    async def _try_dm(self, member, embed):
        """Try to DM a member. Returns True if sent, False if blocked."""
        try:
            await member.send(embed=embed)
            return True
        except discord.Forbidden:
            return False

    def _build_result_embed(self, title, color, mod, target, reason,
                            dm_sent=None, duration=None, proof_url=None):
        """Build a standardized moderation result embed."""
        em = discord.Embed(title=title, color=color)
        em.set_thumbnail(url=target.display_avatar.url)
        em.add_field(name="❌ Moderator", value=f"{mod.mention} ({mod.display_name})", inline=False)
        em.add_field(name="👤 Target", value=f"{target.mention} ({target.display_name})", inline=False)
        if duration:
            em.add_field(name="⏱️ Duration", value=duration, inline=True)
        if dm_sent is not None:
            em.add_field(name="📩 DM", value="Yes" if dm_sent else "No", inline=True)
        if proof_url:
            em.add_field(name="📎 Proof", value=f"[Click to View]({proof_url})", inline=False)
            em.set_image(url=proof_url)
        em.add_field(name="📝 Reason", value=reason, inline=False)
        return em

    # ══════════════════════════════════════════════════════════════
    #  SLASH COMMANDS  (/ prefix — interactive Discord UI)
    # ══════════════════════════════════════════════════════════════

    # ─── /mute ────────────────────────────────────────────────────

    @app_commands.command(name="mute", description="Allows you to timeout a user")
    @app_commands.describe(
        user="The member to mute",
        reason="Reason for the mute",
        dm="Send a DM notification to the user?",
        duration="Duration of the timeout",
        proof="An image that can be considered as proof"
    )
    @app_commands.choices(duration=[
        app_commands.Choice(name="1 minute", value=1),
        app_commands.Choice(name="5 minutes", value=5),
        app_commands.Choice(name="10 minutes", value=10),
        app_commands.Choice(name="30 minutes", value=30),
        app_commands.Choice(name="1 hour", value=60),
        app_commands.Choice(name="6 hours", value=360),
        app_commands.Choice(name="12 hours", value=720),
        app_commands.Choice(name="1 day", value=1440),
        app_commands.Choice(name="7 days", value=10080),
        app_commands.Choice(name="28 days", value=40320),
    ])
    @app_commands.checks.has_permissions(moderate_members=True)
    async def slash_mute(self, interaction: discord.Interaction, user: discord.Member,
                         reason: str = "No reason provided", dm: bool = True,
                         duration: int = 10, proof: discord.Attachment = None):
        await interaction.response.defer()
        td = timedelta(minutes=duration)
        proof_url = proof.url if proof else None

        dm_sent = False
        if dm:
            dm_sent = await self._try_dm(user, discord.Embed(
                title=f"🔇 You have been muted in {interaction.guild.name}",
                description=f"**Duration:** {self._fmt(td)}\n**Reason:** {reason}",
                color=discord.Color.orange()
            ))

        try:
            await user.timeout(td, reason=f"{reason} (by {interaction.user})")
            em = self._build_result_embed("🔇 User Muted", discord.Color.orange(),
                interaction.user, user, reason, dm_sent, self._fmt(td), proof_url)
            await interaction.followup.send(embed=em)
        except discord.Forbidden:
            await interaction.followup.send(embed=self._perm_error(user, "mute"))

    # ─── /unmute ──────────────────────────────────────────────────

    @app_commands.command(name="unmute", description="Allows you to remove the timeout of a user")
    @app_commands.describe(user="The member to unmute", reason="Reason for unmuting")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def slash_unmute(self, interaction: discord.Interaction, user: discord.Member,
                           reason: str = "No reason provided"):
        await interaction.response.defer()
        try:
            await user.timeout(None, reason=f"{reason} (by {interaction.user})")
            em = self._build_result_embed("🔊 User Unmuted", discord.Color.green(),
                interaction.user, user, reason)
            await interaction.followup.send(embed=em)
        except discord.Forbidden:
            await interaction.followup.send(embed=self._perm_error(user, "unmute"))

    # ─── /kick ────────────────────────────────────────────────────

    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The member to kick", reason="Reason for the kick",
        dm="Send a DM notification?", proof="Proof screenshot"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def slash_kick(self, interaction: discord.Interaction, user: discord.Member,
                         reason: str = "No reason provided", dm: bool = True,
                         proof: discord.Attachment = None):
        await interaction.response.defer()
        proof_url = proof.url if proof else None

        dm_sent = False
        if dm:
            dm_sent = await self._try_dm(user, discord.Embed(
                title=f"👢 You have been kicked from {interaction.guild.name}",
                description=f"**Reason:** {reason}", color=discord.Color.orange()
            ))

        try:
            await user.kick(reason=f"{reason} (by {interaction.user})")
            em = self._build_result_embed("👢 User Kicked", discord.Color.orange(),
                interaction.user, user, reason, dm_sent, proof_url=proof_url)
            await interaction.followup.send(embed=em)
        except discord.Forbidden:
            await interaction.followup.send(embed=self._perm_error(user, "kick"))

    # ─── /ban ─────────────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The member to ban", reason="Reason for the ban",
        dm="Send a DM notification?", proof="Proof screenshot"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, user: discord.Member,
                        reason: str = "No reason provided", dm: bool = True,
                        proof: discord.Attachment = None):
        await interaction.response.defer()
        proof_url = proof.url if proof else None

        dm_sent = False
        if dm:
            dm_sent = await self._try_dm(user, discord.Embed(
                title=f"🔨 You have been banned from {interaction.guild.name}",
                description=f"**Reason:** {reason}", color=discord.Color.red()
            ))

        try:
            await user.ban(reason=f"{reason} (by {interaction.user})", delete_message_days=0)
            em = self._build_result_embed("🔨 User Banned", discord.Color.red(),
                interaction.user, user, reason, dm_sent, proof_url=proof_url)
            await interaction.followup.send(embed=em)
        except discord.Forbidden:
            await interaction.followup.send(embed=self._perm_error(user, "ban"))

    # ─── /setrole ─────────────────────────────────────────────────

    @app_commands.command(name="setrole", description="Add a role to a user")
    @app_commands.describe(user="The member", role="The role to add", reason="Reason")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def slash_addrole(self, interaction: discord.Interaction, user: discord.Member,
                            role: discord.Role, reason: str = "No reason provided"):
        await interaction.response.defer()
        try:
            await user.add_roles(role, reason=f"{reason} (by {interaction.user})")
            em = discord.Embed(title="✅ Role Added", color=discord.Color.green())
            em.set_thumbnail(url=user.display_avatar.url)
            em.add_field(name="❌ Moderator", value=f"{interaction.user.mention}", inline=False)
            em.add_field(name="👤 Target", value=f"{user.mention}", inline=True)
            em.add_field(name="🏷️ Role", value=f"{role.mention}", inline=True)
            em.add_field(name="📝 Reason", value=reason, inline=False)
            await interaction.followup.send(embed=em)
        except discord.Forbidden:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Missing Permissions",
                description=f"I can't add **{role.name}** — my role must be higher.",
                color=discord.Color.red()))

    # ─── /removerole ──────────────────────────────────────────────

    @app_commands.command(name="removerole", description="Remove a role from a user")
    @app_commands.describe(user="The member", role="The role to remove", reason="Reason")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def slash_removerole(self, interaction: discord.Interaction, user: discord.Member,
                                role: discord.Role, reason: str = "No reason provided"):
        await interaction.response.defer()
        try:
            await user.remove_roles(role, reason=f"{reason} (by {interaction.user})")
            em = discord.Embed(title="✅ Role Removed", color=discord.Color.orange())
            em.set_thumbnail(url=user.display_avatar.url)
            em.add_field(name="❌ Moderator", value=f"{interaction.user.mention}", inline=False)
            em.add_field(name="👤 Target", value=f"{user.mention}", inline=True)
            em.add_field(name="🏷️ Role", value=f"{role.mention}", inline=True)
            em.add_field(name="📝 Reason", value=reason, inline=False)
            await interaction.followup.send(embed=em)
        except discord.Forbidden:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Missing Permissions",
                description=f"I can't remove **{role.name}** — my role must be higher.",
                color=discord.Color.red()))

    # ─── /purge ───────────────────────────────────────────────────

    @app_commands.command(name="purge", description="Delete messages in bulk")
    @app_commands.describe(amount="Number of messages to delete (max 100)", user="Only delete from this user")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def slash_purge(self, interaction: discord.Interaction, amount: int = 10,
                          user: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        amount = min(max(amount, 1), 100)
        try:
            if user:
                deleted = await interaction.channel.purge(limit=amount, check=lambda m: m.author.id == user.id)
            else:
                deleted = await interaction.channel.purge(limit=amount)
            em = discord.Embed(title="🧹 Messages Purged", color=discord.Color.orange())
            em.add_field(name="❌ Moderator", value=f"{interaction.user.mention}", inline=False)
            em.add_field(name="🗑️ Deleted", value=f"**{len(deleted)}** message(s)", inline=True)
            if user:
                em.add_field(name="👤 From User", value=f"{user.mention}", inline=True)
            await interaction.followup.send(embed=em, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Missing Permissions",
                description="I need **Manage Messages** permission.",
                color=discord.Color.red()), ephemeral=True)

    # ─── /listmuted ───────────────────────────────────────────────

    @app_commands.command(name="listmuted", description="See all currently timed out users")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def slash_listmuted(self, interaction: discord.Interaction):
        await interaction.response.defer()
        muted = [m for m in interaction.guild.members if m.is_timed_out()]
        if not muted:
            em = discord.Embed(title="🔇 Muted Users", description="No users are currently muted!",
                               color=discord.Color.green())
        else:
            desc = "\n".join(f"• {m.mention} — until <t:{int(m.timed_out_until.timestamp())}:R>"
                             for m in muted)
            em = discord.Embed(title=f"🔇 Muted Users ({len(muted)})", description=desc,
                               color=discord.Color.orange())
        await interaction.followup.send(embed=em)

    # ─── Slash command error handler ──────────────────────────────

    async def cog_app_command_error(self, interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            em = discord.Embed(title="❌ No Permission",
                description=f"You need **{', '.join(error.missing_permissions)}** permission.",
                color=discord.Color.red())
        else:
            em = discord.Embed(title="❌ Error", description=f"`{error}`", color=discord.Color.red())

        if interaction.response.is_done():
            await interaction.followup.send(embed=em, ephemeral=True)
        else:
            await interaction.response.send_message(embed=em, ephemeral=True)

    # ══════════════════════════════════════════════════════════════
    #  PREFIX COMMANDS  (! prefix — text fallback)
    # ══════════════════════════════════════════════════════════════

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def prefix_mute(self, ctx, member: discord.Member = None, duration_str: str = "10m", *, reason: str = "No reason provided"):
        """Mute a user.  !mute @user 10m reason"""
        if not member:
            return await ctx.send(embed=discord.Embed(title="❌ Usage", description="`!mute @user [duration] [reason]`", color=discord.Color.red()))

        td = self._parse_duration(duration_str)
        if not td:
            reason = f"{duration_str} {reason}".strip()
            td = timedelta(minutes=10)

        proof_url = ctx.message.attachments[0].url if ctx.message.attachments else None
        dm_sent = await self._try_dm(member, discord.Embed(
            title=f"🔇 You have been muted in {ctx.guild.name}",
            description=f"**Duration:** {self._fmt(td)}\n**Reason:** {reason}", color=discord.Color.orange()))

        try:
            await member.timeout(td, reason=f"{reason} (by {ctx.author})")
            em = self._build_result_embed("🔇 User Muted", discord.Color.orange(), ctx.author, member, reason, dm_sent, self._fmt(td), proof_url)
            await ctx.send(embed=em)
        except discord.Forbidden:
            await ctx.send(embed=self._perm_error(member, "mute"))

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def prefix_unmute(self, ctx, member: discord.Member = None):
        """Unmute a user.  !unmute @user"""
        if not member:
            return await ctx.send(embed=discord.Embed(title="❌ Usage", description="`!unmute @user`", color=discord.Color.red()))
        try:
            await member.timeout(None, reason=f"Unmuted by {ctx.author}")
            em = self._build_result_embed("🔊 User Unmuted", discord.Color.green(), ctx.author, member, "Unmuted")
            await ctx.send(embed=em)
        except discord.Forbidden:
            await ctx.send(embed=self._perm_error(member, "unmute"))

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def prefix_kick(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
        """Kick a user.  !kick @user reason"""
        if not member:
            return await ctx.send(embed=discord.Embed(title="❌ Usage", description="`!kick @user [reason]`", color=discord.Color.red()))
        proof_url = ctx.message.attachments[0].url if ctx.message.attachments else None
        dm_sent = await self._try_dm(member, discord.Embed(title=f"👢 Kicked from {ctx.guild.name}", description=f"**Reason:** {reason}", color=discord.Color.orange()))
        try:
            await member.kick(reason=f"{reason} (by {ctx.author})")
            em = self._build_result_embed("👢 User Kicked", discord.Color.orange(), ctx.author, member, reason, dm_sent, proof_url=proof_url)
            await ctx.send(embed=em)
        except discord.Forbidden:
            await ctx.send(embed=self._perm_error(member, "kick"))

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def prefix_ban(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
        """Ban a user.  !ban @user reason"""
        if not member:
            return await ctx.send(embed=discord.Embed(title="❌ Usage", description="`!ban @user [reason]`", color=discord.Color.red()))
        proof_url = ctx.message.attachments[0].url if ctx.message.attachments else None
        dm_sent = await self._try_dm(member, discord.Embed(title=f"🔨 Banned from {ctx.guild.name}", description=f"**Reason:** {reason}", color=discord.Color.red()))
        try:
            await member.ban(reason=f"{reason} (by {ctx.author})", delete_message_days=0)
            em = self._build_result_embed("🔨 User Banned", discord.Color.red(), ctx.author, member, reason, dm_sent, proof_url=proof_url)
            await ctx.send(embed=em)
        except discord.Forbidden:
            await ctx.send(embed=self._perm_error(member, "ban"))

    @commands.command(name="setrole")
    @commands.has_permissions(manage_roles=True)
    async def prefix_addrole(self, ctx, member: discord.Member = None, *, role: discord.Role = None):
        """Add a role.  !setrole @user @role"""
        if not member or not role:
            return await ctx.send(embed=discord.Embed(title="❌ Usage", description="`!setrole @user @role`", color=discord.Color.red()))
        try:
            await member.add_roles(role, reason=f"Added by {ctx.author}")
            em = discord.Embed(title="✅ Role Added", color=discord.Color.green())
            em.set_thumbnail(url=member.display_avatar.url)
            em.add_field(name="❌ Moderator", value=f"{ctx.author.mention}", inline=False)
            em.add_field(name="👤 Target", value=f"{member.mention}", inline=True)
            em.add_field(name="🏷️ Role", value=f"{role.mention}", inline=True)
            await ctx.send(embed=em)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Missing Permissions", description=f"Can't add **{role.name}**.", color=discord.Color.red()))

    @commands.command(name="removerole")
    @commands.has_permissions(manage_roles=True)
    async def prefix_removerole(self, ctx, member: discord.Member = None, *, role: discord.Role = None):
        """Remove a role.  !removerole @user @role"""
        if not member or not role:
            return await ctx.send(embed=discord.Embed(title="❌ Usage", description="`!removerole @user @role`", color=discord.Color.red()))
        try:
            await member.remove_roles(role, reason=f"Removed by {ctx.author}")
            em = discord.Embed(title="✅ Role Removed", color=discord.Color.orange())
            em.set_thumbnail(url=member.display_avatar.url)
            em.add_field(name="❌ Moderator", value=f"{ctx.author.mention}", inline=False)
            em.add_field(name="👤 Target", value=f"{member.mention}", inline=True)
            em.add_field(name="🏷️ Role", value=f"{role.mention}", inline=True)
            await ctx.send(embed=em)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Missing Permissions", description=f"Can't remove **{role.name}**.", color=discord.Color.red()))

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def prefix_purge(self, ctx, amount: int = 10):
        """Delete messages.  !purge 50"""
        amount = min(max(amount, 1), 100)
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            em = discord.Embed(title="🧹 Messages Purged", color=discord.Color.orange())
            em.add_field(name="🗑️ Deleted", value=f"**{len(deleted)-1}** message(s)", inline=True)
            confirm = await ctx.send(embed=em)
            await confirm.delete(delay=5)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Missing Permissions", description="Need **Manage Messages**.", color=discord.Color.red()))

    # Prefix error handler
    @prefix_mute.error
    @prefix_unmute.error
    @prefix_kick.error
    @prefix_ban.error
    @prefix_addrole.error
    @prefix_removerole.error
    @prefix_purge.error
    async def mod_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(title="❌ No Permission",
                description=f"You need **{', '.join(error.missing_permissions)}**.", color=discord.Color.red()))
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=discord.Embed(title="❌ Invalid Argument",
                description=f"Could not find user/role.\n`{error}`", color=discord.Color.red()))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
