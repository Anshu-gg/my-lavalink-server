"""
Set Prefix Command — Change the bot's command prefix.
"""

import discord
from discord.ext import commands


class SetPrefix(commands.Cog):
    """Change the bot's command prefix."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setprefix")
    @commands.has_permissions(administrator=True)
    async def setprefix_command(self, ctx, new_prefix: str = None):
        """Change the command prefix.  Usage: !setprefix ?"""

        if new_prefix is None:
            cfg = self.bot.load_config(ctx.guild.id)
            current = cfg.get("prefix", "!")
            await ctx.send(f"ℹ️ Current prefix is `{current}`.  Usage: `{current}setprefix <newprefix>`")
            return

        if len(new_prefix) > 5:
            await ctx.send("❌ Prefix must be 5 characters or shorter.")
            return

        # Update config
        cfg = self.bot.load_config(ctx.guild.id)
        old_prefix = cfg.get("prefix", "!")
        cfg["prefix"] = new_prefix
        self.bot.save_config(ctx.guild.id, cfg)

        embed = discord.Embed(
            title="✅ Prefix Updated!",
            description=f"Changed from `{old_prefix}` ➜ `{new_prefix}`",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Example",
            value=f"Try `{new_prefix}help` to see commands",
            inline=False,
        )
        await ctx.send(embed=embed)

    @setprefix_command.error
    async def setprefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission to change the prefix.")


async def setup(bot):
    await bot.add_cog(SetPrefix(bot))
