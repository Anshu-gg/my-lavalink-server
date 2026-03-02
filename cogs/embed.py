"""
Embed Command — Create and send a rich embed message.
"""

import discord
from discord.ext import commands


class Embed(commands.Cog):
    """Send beautiful embedded messages."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="embed")
    async def embed_command(self, ctx, *, content: str = None):
        """Create a rich embed.  Usage: !embed Title | Description | Color(hex)

        Examples:
          !embed Hello World
          !embed My Title | Some description here
          !embed My Title | Some description | #ff5733
        """
        if not content:
            await ctx.send("❌ Please provide at least a title!  Example: `!embed My Title | Description`")
            return

        parts = [p.strip() for p in content.split("|")]

        title = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        color = discord.Color.blue()

        # Optional hex color
        if len(parts) > 2:
            hex_str = parts[2].strip().lstrip("#")
            try:
                color = discord.Color(int(hex_str, 16))
            except ValueError:
                pass  # Fall back to default blue

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        embed.timestamp = ctx.message.created_at

        await ctx.send(embed=embed)

    @commands.command(name="announce")
    async def announce_command(self, ctx, *, content: str = None):
        """Send a fancy announcement embed.  Usage: !announce Your message here"""
        if not content:
            await ctx.send("❌ Please provide an announcement message!")
            return

        embed = discord.Embed(
            title="📢 Announcement",
            description=content,
            color=discord.Color.gold(),
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url,
        )
        embed.timestamp = ctx.message.created_at
        embed.set_footer(text=f"From {ctx.guild.name}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Embed(bot))
