"""
Help Command — Lists all available bot commands in a rich embed.
"""

import discord
from discord.ext import commands


class Help(commands.Cog):
    """Shows a list of all available commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Display all commands with descriptions."""
        cfg = self.bot.load_config(ctx.guild.id)
        prefix = cfg.get("prefix", "!")

        embed = discord.Embed(
            title="📖 Bot Commands",
            description=f"Here are all available commands. Current prefix: `{prefix}`",
            color=discord.Color.blurple(),
        )

        # Loop through every loaded command
        for cmd in sorted(self.bot.commands, key=lambda c: c.name):
            # Use the command's short docstring as the description
            doc = cmd.help or "No description"
            embed.add_field(
                name=f"`{prefix}{cmd.name}`",
                value=doc,
                inline=False,
            )

        embed.set_footer(text="Use the commands above to interact with me!")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
