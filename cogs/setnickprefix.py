"""
Set Nickname Prefix Command — Configure the prefix added to joining members' nicknames.
"""

import discord
from discord.ext import commands


class SetNickPrefix(commands.Cog):
    """Configure the nickname prefix for new members."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setnickprefix")
    @commands.has_permissions(administrator=True)
    async def setnickprefix_command(self, ctx, *, prefix: str = None):
        """Set the nickname prefix for joining members.  Usage: !setnickprefix AC

        When a user joins, their nickname becomes: prefix + name
        For example, if prefix is "AC" and the user is "anshu",
        their nickname becomes "AC anshu".

        Use !setnickprefix off  to disable.
        """

        cfg = self.bot.load_config(ctx.guild.id)

        # Show current setting if no argument
        if prefix is None:
            current = cfg.get("nickname_prefix", "")
            if current:
                await ctx.send(f"ℹ️ Current nickname prefix is `{current}`.  Example: **{current} anshu**")
            else:
                await ctx.send("ℹ️ Nickname prefix is currently **disabled**.")
            return

        # Disable
        if prefix.lower() == "off":
            cfg["nickname_prefix"] = ""
            self.bot.save_config(ctx.guild.id, cfg)

            embed = discord.Embed(
                title="✅ Nickname Prefix Disabled",
                description="New members will keep their original name.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            return

        # Set new prefix
        cfg["nickname_prefix"] = prefix
        self.bot.save_config(ctx.guild.id, cfg)

        embed = discord.Embed(
            title="✅ Nickname Prefix Updated!",
            description=f"New members will be renamed with the prefix `{prefix}`",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Example",
            value=f"If **anshu** joins → nickname becomes **{prefix} anshu**",
            inline=False,
        )
        await ctx.send(embed=embed)

    @setnickprefix_command.error
    async def setnickprefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission to change the nickname prefix.")


async def setup(bot):
    await bot.add_cog(SetNickPrefix(bot))
