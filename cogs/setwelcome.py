"""
Set Welcome Command — Configure the welcome channel and message for new members.
"""

import discord
from discord.ext import commands


class SetWelcome(commands.Cog):
    """Configure the welcome system for new members."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setwelcome")
    @commands.has_permissions(administrator=True)
    async def setwelcome_command(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        """Set the welcome channel and message.  Usage: !setwelcome #channel Welcome, {user}!

        Use {user} in the message to mention the new member.
        """

        if channel is None:
            await ctx.send("❌ Usage: `!setwelcome #channel Welcome message with {user}`")
            return

        cfg = self.bot.load_config(ctx.guild.id)
        cfg["welcome_channel_id"] = str(channel.id)

        if message:
            cfg["welcome_message"] = message

        self.bot.save_config(ctx.guild.id, cfg)

        # Show preview
        preview_text = cfg["welcome_message"].replace("{user}", ctx.author.mention)

        embed = discord.Embed(
            title="✅ Welcome System Updated!",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Channel",
            value=channel.mention,
            inline=True,
        )
        embed.add_field(
            name="Message Preview",
            value=preview_text,
            inline=False,
        )
        embed.set_footer(text="New members will see a welcome embed in the configured channel.")

        await ctx.send(embed=embed)

    @commands.command(name="testwelcome")
    @commands.has_permissions(administrator=True)
    async def testwelcome_command(self, ctx):
        """Preview the welcome message as if you just joined."""
        cfg = self.bot.load_config(ctx.guild.id)
        channel_id = cfg.get("welcome_channel_id")

        if not channel_id:
            await ctx.send("❌ No welcome channel set. Use `!setwelcome #channel` first.")
            return

        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            await ctx.send("❌ The configured welcome channel no longer exists.")
            return

        welcome_text = cfg.get(
            "welcome_message", "Welcome, {user}!"
        ).replace("{user}", ctx.author.mention)

        embed = discord.Embed(
            title="👋 New Member!",
            description=welcome_text,
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Member #{ctx.guild.member_count}  •  This is a test preview")

        await channel.send(embed=embed)
        if channel != ctx.channel:
            await ctx.send(f"✅ Test welcome sent to {channel.mention}!")

    @setwelcome_command.error
    async def setwelcome_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission to configure the welcome system.")


async def setup(bot):
    await bot.add_cog(SetWelcome(bot))
