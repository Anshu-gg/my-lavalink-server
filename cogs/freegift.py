"""
Free Giveaway System — Admins set a free gift, users claim with !free.
Bot DMs the embed to the user and prevents duplicate claims.
"""

import os
import json
import discord
from discord.ext import commands

# File to track who has already claimed
from db import load_claims, save_claims, load_giveaways, save_giveaways

class FreeGiveaway(commands.Cog):
    """Free giveaway system — set a gift and let users claim it."""

    def __init__(self, bot):
        self.bot = bot

    # ─── Admin: Set the free gift ─────────────────────────────────

    @commands.command(name="setfree")
    @commands.has_permissions(administrator=True)
    async def setfree_command(self, ctx, *, content: str = None):
        """Set the free gift message.  Usage: !setfree Title | Description | Link/Code

        Examples:
          !setfree Free Nitro | Claim your free Discord Nitro! | https://gift-link.com
          !setfree Free Wallpaper | Here's an exclusive wallpaper!
        """
        if not content:
            em = discord.Embed(
                title="❌ Invalid Usage",
                description="Usage: `!setfree Title | Description | Link/Code (optional)`",
                color=discord.Color.red()
            )
            await ctx.send(embed=em)
            return

        parts = [p.strip() for p in content.split("|")]
        title = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        gift_link = parts[2] if len(parts) > 2 else ""

        # Save to config
        import time, datetime
        event_id = str(int(time.time()))
        cfg = self.bot.load_config(ctx.guild.id)
        cfg["free_gift"] = {
            "event_id": event_id,
            "title": title,
            "description": description,
            "gift_link": gift_link,
            "active": True,
        }
        self.bot.save_config(ctx.guild.id, cfg)

        g_data = load_giveaways(ctx.guild.id)
        g_data[event_id] = {
            "title": title,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "claims": {}
        }
        save_giveaways(ctx.guild.id, g_data)

        # Reset all previous claims so new gift can be claimed fresh
        save_claims(ctx.guild.id, {})

        embed = discord.Embed(
            title="🎁 Free Gift Set!",
            description=f"**{title}**\n{description}",
            color=discord.Color.gold(),
        )
        if gift_link:
            embed.add_field(name="Gift Link / Code", value=gift_link, inline=False)
        embed.add_field(
            name="How users claim",
            value="Users type `!free` to receive this via DM",
            inline=False,
        )
        embed.set_footer(text="Previous claims have been reset.")
        await ctx.send(embed=embed)

    # ─── Admin: Stop the giveaway ─────────────────────────────────

    @commands.command(name="stopfree")
    @commands.has_permissions(administrator=True)
    async def stopfree_command(self, ctx):
        """Deactivate the current free gift giveaway."""
        cfg = self.bot.load_config(ctx.guild.id)
        event_id = None
        if "free_gift" in cfg:
            cfg["free_gift"]["active"] = False
            event_id = cfg["free_gift"].get("event_id")
            self.bot.save_config(ctx.guild.id, cfg)

        giveaways = load_giveaways(ctx.guild.id)
        if event_id and event_id in giveaways:
            claims = giveaways[event_id].get("claims", {})
        else:
            claims = load_claims(ctx.guild.id)

        total = len(claims)

        embed = discord.Embed(
            title="🛑 Giveaway Ended",
            description=f"The free gift has been deactivated.\n**{total}** user(s) claimed it.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    # ─── User: Claim the free gift ────────────────────────────────

    @commands.command(name="free")
    async def free_command(self, ctx):
        """Claim the current free gift! The bot will DM you the details."""

        cfg = self.bot.load_config(ctx.guild.id)
        gift = cfg.get("free_gift")

        # Check if there's an active giveaway
        if not gift or not gift.get("active"):
            em = discord.Embed(
                title="❌ No Active Gift",
                description="There's no active free gift right now. Check back later!",
                color=discord.Color.red()
            )
            await ctx.send(embed=em)
            return

        # Check if user already claimed
        import time, datetime
        event_id = gift.get("event_id")
        g_data = load_giveaways(ctx.guild.id)
        
        # Migrate old active giveaway
        if not event_id:
            event_id = str(int(time.time()))
            gift["event_id"] = event_id
            cfg["free_gift"] = gift
            self.bot.save_config(ctx.guild.id, cfg)
            g_data[event_id] = {
                "title": gift.get("title", "Legacy Gift"),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "claims": load_claims(ctx.guild.id)
            }
            save_giveaways(ctx.guild.id, g_data)

        event = g_data.get(event_id, {})
        claims = event.get("claims", {})
        user_id = str(ctx.author.id)

        if user_id in claims:
            embed = discord.Embed(
                title="⚠️ Already Claimed!",
                description="You have already claimed the goodies! You cannot claim again.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            return

        # Build the gift embed to DM — use custom embed data if available
        embed_data = gift.get("embed", {})

        # Parse color
        color = discord.Color.gold()
        color_hex = embed_data.get("color", "")
        if color_hex:
            try:
                color = discord.Color(int(color_hex.lstrip("#"), 16))
            except ValueError:
                pass

        # Function to replace variables
        def replace_vars(text):
            if not text or not isinstance(text, str):
                return text
            # Fix accidental unclosed braces from typo: "{user" -> "{user}"
            t = text.replace("{user ", "{user} ")
            if t.endswith("{user"):
                t = t + "}"

            t = t.replace("{user}", ctx.author.mention)
            t = t.replace("{username}", ctx.author.display_name)
            
            # Icon URL replacement
            icon_url = str(ctx.author.display_avatar.url) if ctx.author.display_avatar else ""
            t = t.replace("{usericonurl}", icon_url)
            
            return t

        dm_embed = discord.Embed(
            title=replace_vars(f"🎁 {gift.get('title', 'Free Gift')}"),
            description=replace_vars(gift.get("description", "")),
            color=color,
        )

        # Author
        author_name = str(replace_vars(embed_data.get("author_name", "")) or "")
        author_icon = str(replace_vars(embed_data.get("author_icon", "")) or "")
        if author_name:
            if not author_icon.startswith("http"):
                author_icon = None
            dm_embed.set_author(name=author_name, icon_url=author_icon or None)

        # Thumbnail
        thumb_url = str(replace_vars(embed_data.get("thumbnail", "")) or "")
        if thumb_url and thumb_url.startswith("http"):
            dm_embed.set_thumbnail(url=thumb_url)

        # Large image
        img_url = str(replace_vars(embed_data.get("image", "")) or "")
        if img_url and img_url.startswith("http"):
            dm_embed.set_image(url=img_url)

        # Custom fields
        for field in embed_data.get("fields", []):
            if field.get("name") and field.get("value"):
                dm_embed.add_field(
                    name=replace_vars(field["name"]),
                    value=replace_vars(field["value"]),
                    inline=field.get("inline", False),
                )

        # Gift link as a field
        gift_link = replace_vars(gift.get("gift_link", ""))
        if gift_link:
            dm_embed.add_field(name="🔗 Your Gift", value=gift_link, inline=False)

        # Footer
        footer_text = str(replace_vars(embed_data.get("footer_text", "")) or "")
        if not footer_text:
            footer_text = f"From {ctx.guild.name} • Enjoy your gift!"
        
        footer_icon = str(replace_vars(embed_data.get("footer_icon", "")) or "")
        if not footer_icon.startswith("http"):
            footer_icon = None
            
        dm_embed.set_footer(text=footer_text, icon_url=footer_icon or None)
        dm_embed.timestamp = ctx.message.created_at

        # Try to DM the user
        try:
            message_text = replace_vars(gift.get("message_text", ""))
            await ctx.author.send(content=message_text or None, embed=dm_embed)

            # Record the claim
            claims[user_id] = {
                "username": str(ctx.author),
                "avatar": str(ctx.author.display_avatar.url) if ctx.author.display_avatar else None,
                "claimed_at": str(ctx.message.created_at),
            }
            if event_id not in g_data:
                g_data[event_id] = {"title": gift.get("title", "Gift"), "created_at": str(ctx.message.created_at), "claims": {}}
            g_data[event_id]["claims"] = claims
            save_giveaways(ctx.guild.id, g_data)
            save_claims(ctx.guild.id, claims)

            # Confirm in the channel
            confirm = discord.Embed(
                title="✅ Gift Sent!",
                description=f"{ctx.author.mention}, check your DMs! 🎉",
                color=discord.Color.green(),
            )
            await ctx.send(embed=confirm)

        except discord.Forbidden:
            em = discord.Embed(
                title="❌ Cannot Send DM",
                description=f"{ctx.author.mention}, I can't DM you! Please enable **DMs from server members** in your privacy settings and try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=em)
            
        except discord.HTTPException as e:
            em = discord.Embed(
                title="❌ Invalid Embed Data",
                description=f"Could not send the gift embed because it contains invalid data (like a broken URL).\n`{e}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=em)

        except Exception as e:
            print(f"Error in free: {e}")
            import traceback
            traceback.print_exc()
            em = discord.Embed(
                title="❌ Unexpected Error",
                description=f"An unexpected error occurred: `{e}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=em)

    # ─── Error handlers ───────────────────────────────────────────

    @setfree_command.error
    async def setfree_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            em = discord.Embed(
                title="❌ No Permission",
                description="You need **Administrator** permission to set free gifts.",
                color=discord.Color.red()
            )
            await ctx.send(embed=em)

    @stopfree_command.error
    async def stopfree_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            em = discord.Embed(
                title="❌ No Permission",
                description="You need **Administrator** permission to stop giveaways.",
                color=discord.Color.red()
            )
            await ctx.send(embed=em)


async def setup(bot):
    await bot.add_cog(FreeGiveaway(bot))
