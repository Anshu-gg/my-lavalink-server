"""
DM Command — Send a direct message to a mentioned user.
"""

import discord
from discord.ext import commands


class DirectMessage(commands.Cog):
    """Send direct messages to users."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dm")
    @commands.has_permissions(administrator=True)
    async def dm_command(self, ctx, member: discord.Member = None, *, message: str = None):
        """DM a user.  Usage: !dm @user Your message here"""

        if member is None or message is None:
            await ctx.send("❌ Usage: `!dm @user Your message here`")
            return

        # Build a nice embed for the DM
        embed = discord.Embed(
            title=f"📬 Message from {ctx.guild.name}",
            description=message,
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Sent by {ctx.author.display_name}")
        embed.timestamp = ctx.message.created_at

        try:
            await member.send(embed=embed)
            # Confirm in the channel
            confirm = discord.Embed(
                title="✅ DM Sent!",
                description=f"Successfully sent a DM to {member.mention}",
                color=discord.Color.green(),
            )
            await ctx.send(embed=confirm)

        except discord.Forbidden:
            await ctx.send(f"❌ Could not DM {member.mention}. They may have DMs disabled.")

        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @dm_command.error
    async def dm_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission to use this command.")


async def setup(bot):
    await bot.add_cog(DirectMessage(bot))
