import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timezone

from db import load_feedback_claims, save_feedback_claims, load_feedback_events, save_feedback_events

class FeedbackGift(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="reward", help="Claim the active feedback reward.")
    async def claim_reward(self, ctx):
        cfg = self.bot.load_config(ctx.guild.id)
        gift = cfg.get("feedback_gift", {})

        if not gift or not gift.get("active"):
            em = discord.Embed(
                title="❌ No Active Reward",
                description="There is no active reward event at the moment. Check back later!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=em)

        event_id = gift.get("event_id")
        user_id_str = str(ctx.author.id)
        
        # Load claims to check if already claimed
        g_data = load_feedback_events(ctx.guild.id)
        legacy_claims = load_feedback_claims(ctx.guild.id)
        claims = {}
        
        if event_id and event_id in g_data:
            claims = g_data[event_id].get("claims", {})
        else:
            claims = legacy_claims

        if user_id_str in claims:
            em = discord.Embed(
                title="⚠️ Already Claimed!",
                description=f"{ctx.author.mention}, you have already claimed this reward! You cannot claim again.",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=em)

        # Send DM
        try:
            embed_cfg = gift.get("embed", {})
            embed = discord.Embed(
                title=gift.get("title", ""),
                description=gift.get("description", ""),
                color=discord.Color.from_str(embed_cfg.get("color", "#FFD700")) if embed_cfg.get("color") else discord.Color.default()
            )

            # Author
            if embed_cfg.get("author_name"):
                embed.set_author(
                    name=embed_cfg["author_name"],
                    icon_url=embed_cfg.get("author_icon", "") or None
                )

            # Images
            if embed_cfg.get("thumbnail"):
                embed.set_thumbnail(url=embed_cfg["thumbnail"])
            if embed_cfg.get("image"):
                embed.set_image(url=embed_cfg["image"])

            # Fields
            for field in embed_cfg.get("fields", []):
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False)
                )

            # The actual gift link as a field
            if gift.get("gift_link"):
                embed.add_field(name="🔗 Your Reward", value=gift["gift_link"], inline=False)

            # Footer
            if embed_cfg.get("footer_text"):
                embed.set_footer(
                    text=embed_cfg["footer_text"],
                    icon_url=embed_cfg.get("footer_icon", "") or None
                )

            # Send Initial DM
            msg_text = gift.get("message_text", f"Hey {ctx.author.mention}, here is your reward!")
            await ctx.author.send(content=msg_text, embed=embed)

        except discord.Forbidden:
            em = discord.Embed(
                title="❌ Cannot Send DM",
                description=f"{ctx.author.mention}, I can't DM you! Please enable **DMs from server members** in your privacy settings and try again.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=em)
        except Exception as e:
            em = discord.Embed(
                title="❌ Error",
                description=f"{ctx.author.mention}, an error occurred while sending your DM.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=em)

        # Save Claim tracking
        avatar_url = ctx.author.display_avatar.url if ctx.author.display_avatar else ""
        claim_info = {
            "username": str(ctx.author),
            "avatar": avatar_url,
            "claimed_at": datetime.now(timezone.utc).isoformat()
        }
        
        if event_id and event_id in g_data:
            g_data[event_id].setdefault("claims", {})[user_id_str] = claim_info
            save_feedback_events(ctx.guild.id, g_data)
        else:
            legacy_claims[user_id_str] = claim_info
            save_feedback_claims(ctx.guild.id, legacy_claims)
            
        em = discord.Embed(
            title="✅ Reward Sent!",
            description=f"{ctx.author.mention}, check your DMs! 🎉",
            color=discord.Color.green()
        )
        await ctx.send(embed=em)

        # Provide follow-up prompt in DM
        try:
            prompt_text = gift.get("response_prompt", "Please reply to this DM with your feedback/response!")
            await ctx.author.send(f"\n**💬 {prompt_text}**")
        except:
            pass # We know we could DM them a second ago

        # Wait for user's next response in the DM
        def check(m):
            return m.author == ctx.author and m.channel == ctx.author.dm_channel

        try:
            response_msg = await self.bot.wait_for('message', check=check, timeout=300.0) # wait up to 5 mins
        except asyncio.TimeoutError:
            try:
                await ctx.author.send("⏱️ The feedback window has expired. Thank you!")
            except:
                pass
            return 

        # Forward the response
        log_channel_id = gift.get("log_channel_id", "").strip()
        admin_id = gift.get("admin_id", "").strip()
        
        # Save response text to their claim
        if event_id and event_id in g_data:
            if user_id_str in g_data[event_id].setdefault("claims", {}):
                g_data[event_id]["claims"][user_id_str]["response"] = response_msg.content
                save_feedback_events(ctx.guild.id, g_data)
        else:
            if user_id_str in legacy_claims:
                legacy_claims[user_id_str]["response"] = response_msg.content
                save_feedback_claims(ctx.guild.id, legacy_claims)
        
        if not log_channel_id:
            try:
                await ctx.author.send("✅ Thank you for your response! (Note: No log channel was configured).")
            except:
                pass
            return
            
        try:
            log_channel = self.bot.get_channel(int(log_channel_id))
            if not log_channel:
                try:
                    await ctx.author.send("✅ Thank you for your response! (Note: The configured log channel could not be found).")
                except: pass
                return
                
            admin_ping = f"<@{admin_id}>" if admin_id else ""
            
            fb_embed = discord.Embed(
                title="New Reward Feedback Received!",
                description=response_msg.content,
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            fb_embed.set_author(name=str(ctx.author), icon_url=avatar_url)
            fb_embed.set_footer(text=f"User ID: {ctx.author.id}")
            
            # handle attachments if any
            if response_msg.attachments:
                fb_embed.set_image(url=response_msg.attachments[0].url)
                
            await log_channel.send(content=f"{admin_ping} A user submitted feedback after claiming **{gift.get('title', 'Reward')}**!", embed=fb_embed)
            
            try:
                await ctx.author.send("✅ Thanks! Your response has been securely forwarded to the admins.")
            except: pass
            
        except Exception as e:
            try:
                await ctx.author.send("✅ Thank you! But an error happened trying to forward it.")
            except: pass

async def setup(bot):
    await bot.add_cog(FeedbackGift(bot))
