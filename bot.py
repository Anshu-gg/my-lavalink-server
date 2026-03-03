"""
Discord Bot — Main Entry Point
Loads all cogs from the /cogs folder and starts the bot.
"""

import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import threading

# Load environment variables from .env
load_dotenv()

# ─── Config Helper ────────────────────────────────────────────────
from db import load_config, save_config, load_server_logins, save_server_logins

# ─── Dynamic Prefix ──────────────────────────────────────────────
def get_prefix(bot, message):
    """Return the current prefix for the guild."""
    guild_id = message.guild.id if message.guild else None
    cfg = load_config(guild_id)
    return commands.when_mentioned_or(cfg.get("prefix", "!"))(bot, message)

# ─── Customized Bot Class ──────────────────────────────────────────
class MeteorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        """Standard initialization point for discord.py commands.Bot."""
        print("📡 LOUD: Entering setup_hook()...", flush=True)
        
        # Start the web dashboard in a background thread
        from dashboard import run_dashboard
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        print("🌐 LOUD: Dashboard thread started on background.", flush=True)

        # Load Cogs
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_name = f"cogs.{filename[:-3]}"
                print(f"📡 LOUD: Attempting to load extension: {cog_name}", flush=True)
                try:
                    await self.load_extension(cog_name)
                    print(f"✅ LOUD: Successfully loaded: {cog_name}", flush=True)
                except Exception as e:
                    print(f"❌ LOUD: Failed to load {cog_name}: {e}", flush=True)
        
        print("📡 LOUD: setup_hook() complete.", flush=True)

# ─── Create the Bot ──────────────────────────────────────────────
bot = MeteorBot()

# Attach helpers to the bot so cogs can use them
bot.load_config = load_config
bot.save_config = save_config

def get_commands_list():
    """Return a list of all loaded commands with name, help, and cog info."""
    result = []
    for cmd in sorted(bot.commands, key=lambda c: c.name):
        result.append({
            "name": cmd.name,
            "help": cmd.help or "No description",
            "cog": cmd.cog_name or "Core",
            "admin_only": any(
                isinstance(check, commands.has_permissions)
                for check in getattr(cmd, "checks", [])
            ),
        })
    return result

bot.get_commands_list = get_commands_list

# ─── Owner Dashboard Credential Commands ──────────────────────────
@bot.command(name="addlogin", help="[Owner Only] Add dashboard login for a Server ID.")
@commands.is_owner()
async def addlogin(ctx, guild_id: str, login_id: str, password: str):
    logins = load_server_logins()
    logins[guild_id] = {"login_id": login_id, "password": password}
    save_server_logins(logins)
    await ctx.reply(f"✅ Dashboard credentials saved for guild `{guild_id}`.")

@bot.command(name="removelogin", help="[Owner Only] Remove dashboard login for a Server ID.")
@commands.is_owner()
async def removelogin(ctx, guild_id: str):
    logins = load_server_logins()
    if guild_id in logins:
        del logins[guild_id]
        save_server_logins(logins)
        await ctx.reply(f"🗑️ Removed dashboard credentials for guild `{guild_id}`.")
    else:
        await ctx.reply(f"❌ No credentials found.")

# ─── Events ──────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"\n🤖 Bot is online! Logged in as {bot.user}", flush=True)
    print(f"📡 Serving {len(bot.guilds)} server(s)", flush=True)
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print(f"⚡ Synced slash commands to {len(bot.guilds)} server(s)", flush=True)
    except Exception as e:
        print(f"⚠️ Failed to sync slash commands: {e}", flush=True)
    await bot.change_presence(activity=discord.Game(name="!help for commands"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    import traceback
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    try:
        await ctx.send(f"❌ An error occurred: `{error}`")
    except:
        pass

@bot.event
async def on_member_join(member):
    cfg = load_config(member.guild.id)
    nick_prefix = cfg.get("nickname_prefix", "")
    if nick_prefix:
        new_nick = f"{nick_prefix} {member.display_name}"
        try:
            await member.edit(nick=new_nick)
        except:
            pass
    channel_id = cfg.get("welcome_channel_id")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            welcome_text = cfg.get("welcome_message", "Welcome, {user}!").replace("{user}", member.mention)
            embed = discord.Embed(title="👋 New Member!", description=welcome_text, color=discord.Color.green())
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

# ─── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token and token != "your-bot-token-here":
        print(f"📡 LOUD: Starting bot with token prefix: {token[:10]}...", flush=True)
        bot.run(token)
    else:
        # Emergency keep-alive for dashboard if token is missing
        print("❌ LOUD: No valid DISCORD_TOKEN found. Only dashboard will start.", flush=True)
        from dashboard import run_dashboard
        run_dashboard()
