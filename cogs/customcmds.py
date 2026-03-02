"""
Custom Commands — Handles user-defined commands from the dashboard.
Commands are stored in config.json under "custom_commands".
Supports: text replies, embed replies, and moderation actions
(mute/timeout, kick, ban, add role, remove role, purge).
"""

import os
import json
import re
import discord
from discord.ext import commands
from datetime import timedelta


class CustomCommands(commands.Cog):
    """Handles custom commands created from the dashboard."""

    def __init__(self, bot):
        self.bot = bot
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _replace_vars(self, text, message, target=None):
        """Replace variables in text with actual values."""
        if not text:
            return text
        text = text.replace("{user}", message.author.mention)
        text = text.replace("{username}", message.author.display_name)
        text = text.replace("{server}", message.guild.name if message.guild else "DM")
        if target:
            text = text.replace("{target}", target.mention)
            text = text.replace("{targetname}", target.display_name)
        return text

    def _parse_target(self, message, args_text):
        """Try to resolve a mentioned user from the message or raw text."""
        # Check mentions first
        if message.mentions:
            return message.mentions[0]
        # Try to parse a user ID from the args
        if args_text:
            match = re.search(r'(\d{17,20})', args_text)
            if match:
                member = message.guild.get_member(int(match.group(1)))
                if member:
                    return member
        return None

    def _parse_duration(self, args_text):
        """Parse duration from text like '10m', '1h', '30s', '1d'."""
        if not args_text:
            return None
        match = re.search(r'(\d+)\s*([smhd])', args_text.lower())
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit == 's':
                return timedelta(seconds=amount)
            elif unit == 'm':
                return timedelta(minutes=amount)
            elif unit == 'h':
                return timedelta(hours=amount)
            elif unit == 'd':
                return timedelta(days=amount)
        return None

    async def _execute_action(self, message, action, args_text, cmd_data):
        """Execute a moderation action."""
        if not message.guild:
            return await message.channel.send(embed=discord.Embed(
                title="❌ Error", description="This command can only be used in a server.",
                color=discord.Color.red()
            ))

        target = self._parse_target(message, args_text)

        # ─── Purge doesn't need a target user ───
        if action == "purge":
            match = re.search(r'(\d+)', args_text) if args_text else None
            count = int(match.group(1)) if match else 10
            count = min(count, 100)  # Cap at 100
            try:
                deleted = await message.channel.purge(limit=count + 1)  # +1 for the command itself
                em = discord.Embed(
                    title="🧹 Messages Purged",
                    description=f"Deleted **{len(deleted) - 1}** message(s).",
                    color=discord.Color.orange()
                )
                confirm = await message.channel.send(embed=em)
                await confirm.delete(delay=3)
            except discord.Forbidden:
                await message.channel.send(embed=discord.Embed(
                    title="❌ Missing Permissions",
                    description="I need **Manage Messages** permission to purge.",
                    color=discord.Color.red()
                ))
            return

        # All other actions need a target
        if not target:
            return await message.channel.send(embed=discord.Embed(
                title="❌ No Target",
                description="Please mention a user. Example: `!command @user`",
                color=discord.Color.red()
            ))

        # Don't let them target the bot or themselves
        if target.id == self.bot.user.id:
            return await message.channel.send(embed=discord.Embed(
                title="❌ Error", description="I can't do that to myself!",
                color=discord.Color.red()
            ))

        try:
            if action == "mute":
                duration = self._parse_duration(args_text)
                if not duration:
                    duration = timedelta(minutes=int(cmd_data.get("action_duration", 10)))
                await target.timeout(duration)
                return await self._send_action_response(message, cmd_data, target,
                    fallback_title=f"🔇 {target.display_name} Muted",
                    fallback_desc=f"{target.mention} has been timed out for {self._format_duration(duration)}."
                )

            elif action == "kick":
                reason = cmd_data.get("action_reason", f"Kicked by {message.author}")
                await target.kick(reason=reason)
                return await self._send_action_response(message, cmd_data, target,
                    fallback_title=f"👢 {target.display_name} Kicked",
                    fallback_desc=f"{target.mention} has been kicked from the server."
                )

            elif action == "ban":
                reason = cmd_data.get("action_reason", f"Banned by {message.author}")
                await target.ban(reason=reason, delete_message_days=0)
                return await self._send_action_response(message, cmd_data, target,
                    fallback_title=f"🔨 {target.display_name} Banned",
                    fallback_desc=f"{target.mention} has been banned from the server."
                )

            elif action == "addrole":
                role_id = cmd_data.get("action_role_id", "")
                if not role_id:
                    return await message.channel.send(embed=discord.Embed(
                        title="❌ Config Error",
                        description="No role ID configured for this command.",
                        color=discord.Color.red()
                    ))
                role = message.guild.get_role(int(role_id))
                if not role:
                    return await message.channel.send(embed=discord.Embed(
                        title="❌ Error",
                        description="The configured role was not found.",
                        color=discord.Color.red()
                    ))
                await target.add_roles(role)
                return await self._send_action_response(message, cmd_data, target,
                    fallback_title=f"✅ Role Added",
                    fallback_desc=f"Added **{role.name}** to {target.mention}."
                )

            elif action == "removerole":
                role_id = cmd_data.get("action_role_id", "")
                if not role_id:
                    return await message.channel.send(embed=discord.Embed(
                        title="❌ Config Error",
                        description="No role ID configured for this command.",
                        color=discord.Color.red()
                    ))
                role = message.guild.get_role(int(role_id))
                if not role:
                    return await message.channel.send(embed=discord.Embed(
                        title="❌ Error",
                        description="The configured role was not found.",
                        color=discord.Color.red()
                    ))
                await target.remove_roles(role)
                return await self._send_action_response(message, cmd_data, target,
                    fallback_title=f"✅ Role Removed",
                    fallback_desc=f"Removed **{role.name}** from {target.mention}."
                )

            elif action == "unmute":
                await target.timeout(None)
                return await self._send_action_response(message, cmd_data, target,
                    fallback_title=f"🔊 {target.display_name} Unmuted",
                    fallback_desc=f"{target.mention} has been unmuted."
                )

        except discord.Forbidden:
            await message.channel.send(embed=discord.Embed(
                title="❌ Missing Permissions",
                description=f"I don't have permission to **{action}** {target.mention}. "
                            "Make sure my role is higher than theirs.",
                color=discord.Color.red()
            ))
        except Exception as e:
            await message.channel.send(embed=discord.Embed(
                title="❌ Error",
                description=f"Failed to execute action: `{e}`",
                color=discord.Color.red()
            ))

    async def _send_action_response(self, message, cmd_data, target, fallback_title, fallback_desc):
        """Send the response embed — use custom embed if configured, otherwise fallback."""
        response_type = cmd_data.get("type", "none")

        if response_type == "embed":
            embed_data = cmd_data.get("embed", {})
            color = discord.Color.blurple()
            color_hex = embed_data.get("color", "")
            if color_hex:
                try:
                    color = discord.Color(int(color_hex.lstrip("#"), 16))
                except ValueError:
                    pass

            em = discord.Embed(
                title=self._replace_vars(embed_data.get("title", ""), message, target),
                description=self._replace_vars(embed_data.get("description", ""), message, target),
                color=color,
            )
            if embed_data.get("image"):
                em.set_image(url=embed_data["image"])
            if embed_data.get("thumbnail"):
                em.set_thumbnail(url=embed_data["thumbnail"])
            if embed_data.get("footer_text"):
                em.set_footer(
                    text=self._replace_vars(embed_data["footer_text"], message, target),
                    icon_url=embed_data.get("footer_icon") or None
                )
            await message.channel.send(embed=em)

        elif response_type == "text":
            response = cmd_data.get("response", "")
            if response:
                await message.channel.send(self._replace_vars(response, message, target))
            else:
                # Fallback
                await message.channel.send(embed=discord.Embed(
                    title=fallback_title, description=fallback_desc,
                    color=discord.Color.green()
                ))
        else:
            # No custom response configured — use fallback
            await message.channel.send(embed=discord.Embed(
                title=fallback_title, description=fallback_desc,
                color=discord.Color.green()
            ))

    def _format_duration(self, td):
        """Format a timedelta into a readable string."""
        total = int(td.total_seconds())
        if total < 60:
            return f"{total}s"
        elif total < 3600:
            return f"{total // 60}m"
        elif total < 86400:
            return f"{total // 3600}h"
        else:
            return f"{total // 86400}d"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for custom command triggers."""
        if message.author.bot:
            return
        if not message.guild:
            return

        cfg = self.bot.load_config(ctx.guild.id)
        prefix = cfg.get("prefix", "!")
        custom_cmds = cfg.get("custom_commands", {})

        if not custom_cmds:
            return
        if not message.content.startswith(prefix):
            return

        # Extract command name and remaining args
        content_after_prefix = message.content[len(prefix):].strip()
        parts = content_after_prefix.split(None, 1)
        cmd_name = parts[0].lower() if parts else ""
        args_text = parts[1] if len(parts) > 1 else ""

        if not cmd_name or cmd_name not in custom_cmds:
            return

        # Don't intercept built-in commands
        if self.bot.get_command(cmd_name):
            return

        cmd_data = custom_cmds[cmd_name]

        # Check admin-only
        if cmd_data.get("admin_only", False):
            if not message.author.guild_permissions.administrator:
                em = discord.Embed(
                    title="❌ No Permission",
                    description="This command requires **Administrator** permission.",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=em)
                return

        # Check if this command has an action
        action = cmd_data.get("action", "none")

        if action and action != "none":
            await self._execute_action(message, action, args_text, cmd_data)
            return

        # No action — just send response
        cmd_type = cmd_data.get("type", "text")

        if cmd_type == "embed":
            embed_data = cmd_data.get("embed", {})
            color = discord.Color.blurple()
            color_hex = embed_data.get("color", "")
            if color_hex:
                try:
                    color = discord.Color(int(color_hex.lstrip("#"), 16))
                except ValueError:
                    pass

            em = discord.Embed(
                title=self._replace_vars(embed_data.get("title", ""), message),
                description=self._replace_vars(embed_data.get("description", ""), message),
                color=color,
            )
            if embed_data.get("image"):
                em.set_image(url=embed_data["image"])
            if embed_data.get("thumbnail"):
                em.set_thumbnail(url=embed_data["thumbnail"])
            if embed_data.get("footer_text"):
                em.set_footer(
                    text=self._replace_vars(embed_data["footer_text"], message),
                    icon_url=embed_data.get("footer_icon") or None
                )
            await message.channel.send(embed=em)

        else:
            response = cmd_data.get("response", "")
            if response:
                response = self._replace_vars(response, message)
                await message.channel.send(response)


async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
