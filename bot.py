"""
Discord Bot — Main Entry Point
Loads all cogs from the /cogs folder and starts the bot.
"""

import sys
import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

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


# ─── Create the Bot ──────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True   # Required for reading message text
intents.members = True           # Required for member join events

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,           # We'll make our own help command
)

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

@bot.command(name="addlogin", help="[Owner Only] Add dashboard login for a Server ID. Usage: !addlogin <server_id> <login_id> <password>")
@commands.is_owner()
async def addlogin(ctx, guild_id: str, login_id: str, password: str):
    """Assign a Dashboard Login ID and Password for a specific server."""
    logins = load_server_logins()
    logins[guild_id] = {"login_id": login_id, "password": password}
    save_server_logins(logins)
    await ctx.reply(f"✅ Dashboard credentials saved for guild `{guild_id}`.\n**Login ID:** `{login_id}`\n**Password:** `{password}`")

@bot.command(name="removelogin", help="[Owner Only] Remove dashboard login for a Server ID.")
@commands.is_owner()
async def removelogin(ctx, guild_id: str):
    """Remove a Dashboard Login ID for a specific server."""
    logins = load_server_logins()
    if guild_id in logins:
        del logins[guild_id]
        save_server_logins(logins)
        await ctx.reply(f"🗑️ Removed dashboard credentials for guild `{guild_id}`.")
    else:
        await ctx.reply(f"❌ No credentials found for guild `{guild_id}`.")

# ─── Events ──────────────────────────────────────────────────────

@bot.event
async def on_ready():
    """Fires once when the bot is connected and ready."""
    print(f"\n🤖 Bot is online!  Logged in as {bot.user}")
    print(f"📡 Serving {len(bot.guilds)} server(s)")

    # Sync slash commands to all guilds (instant, not global)
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print(f"⚡ Synced slash commands to {len(bot.guilds)} server(s)")
    except Exception as e:
        print(f"⚠️ Failed to sync slash commands: {e}")

    await bot.change_presence(
        activity=discord.Game(name="!help for commands")
    )
    print()


@bot.event
async def on_command_error(ctx, error):
    """Global error handler to prevent silent command failures."""
    if isinstance(error, commands.CommandNotFound):
        return
    import traceback
    print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    try:
        await ctx.send(f"❌ An error occurred during command execution: `{error}`")
    except:
        pass


@bot.event
async def on_member_join(member):
    """Set nickname prefix and send a welcome embed when a new member joins."""
    cfg = load_config(member.guild.id)

    # ── Set nickname prefix (e.g. "AC anshu") ──
    nick_prefix = cfg.get("nickname_prefix", "")
    if nick_prefix:
        new_nick = f"{nick_prefix} {member.display_name}"
        try:
            await member.edit(nick=new_nick)
            print(f"✅ Set nickname for {member} → {new_nick}")
        except discord.Forbidden:
            print(f"⚠️ Cannot change nickname for {member} (missing permissions or owner)")
        except Exception as e:
            print(f"⚠️ Nickname error for {member}: {e}")

    # ── Send welcome embed ──
    channel_id = cfg.get("welcome_channel_id")

    if not channel_id:
        return  # No welcome channel configured yet

    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return

    # Build the welcome message — replace {user} with a mention
    welcome_text = cfg.get(
        "welcome_message",
        "Welcome, {user}!"
    ).replace("{user}", member.mention)

    embed = discord.Embed(
        title="👋 New Member!",
        description=welcome_text,
        color=discord.Color.green(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member #{member.guild.member_count}")

    await channel.send(embed=embed)


# ─── Load Cogs ───────────────────────────────────────────────────

async def load_cogs():
    """Dynamically load every .py file inside the cogs/ folder."""
    print("📡 LOUD: Entering load_cogs()...")
    cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            cog_name = f"cogs.{filename[:-3]}"
            print(f"📡 LOUD: Attempting to load extension: {cog_name}")
            try:
                await bot.load_extension(cog_name)
                print(f"✅ LOUD: Successfully loaded: {cog_name}")
            except Exception as e:
                print(f"❌ LOUD: Failed to load {cog_name}: {e}")
    print("📡 LOUD: Finished load_cogs().")


import asyncio
import threading


async def main():
    # Start the web dashboard in a background thread
    from dashboard import run_dashboard
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    print("🌐 LOUD: Dashboard thread started!")
    print("🌐 LOUD: Dashboard running at http://localhost:5000")

    # Check token before trying to connect
    token = os.getenv("DISCORD_TOKEN")
    print(f"📡 LOUD: Attempting to start bot with token prefix: {token[:10] if token else 'NONE'}...")
    if not token or token == "your-bot-token-here":
        print("\n" + "=" * 55)
        print("❌ ERROR: No valid bot token found!")
        print("=" * 55)
        print("👉 Open the .env file and replace")
        print('   DISCORD_TOKEN=your-bot-token-here')
        print("   with your actual bot token from:")
        print("   https://discord.com/developers/applications")
        print("=" * 55)
        print("\n🌐 Dashboard is still running at http://localhost:5000")
        print("   Press Ctrl+C to stop.\n")
        # Keep alive so the dashboard stays running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        return

    async with bot:
        print("📡 LOUD: Starting load_cogs() inside async with...")
        await load_cogs()
        print("📡 LOUD: Calling bot.start()...")
        await bot.start(token)

asyncio.run(main())
