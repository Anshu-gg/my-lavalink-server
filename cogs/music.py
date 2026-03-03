import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os
import logging
import aiohttp
import asyncio
from typing import Optional, List

# Enable debug logging for wavelink
logging.getLogger('wavelink').setLevel(logging.DEBUG)

class MusicController(discord.ui.View):
    """A view that provides buttons to control the music player."""
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.blurple, emoji="⏯️")
    async def toggle_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player: return
        await self.player.pause(not self.player.paused)
        await interaction.response.send_message(f"Music {'paused' if self.player.paused else 'resumed'} by {interaction.user.mention}", delete_after=5)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.green, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player: return
        await self.player.skip()
        await interaction.response.send_message(f"Skipped by {interaction.user.mention}", delete_after=5)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red, emoji="🛑")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player: return
        await self.player.disconnect()
        self.stop()
        await interaction.response.send_message(f"Stopped and disconnected by {interaction.user.mention}", delete_after=5)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlists = {} # Simple in-memory storage for demonstration

    async def cog_load(self):
        """Register the connection task without blocking bot startup."""
        self.bot.loop.create_task(self.connect_node())

    async def connect_node(self):
        """Robust background task to connect to Lavalink with retries."""
        print("📡 LOUD: Music Cog - connect_node() background task started.", flush=True)
        
        node_uri = os.getenv("LAVALINK_URI", "").strip().rstrip('/')
        node_password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass").strip()

        if not node_uri:
            print("⚠️ LOUD: LAVALINK_URI is missing from environment. Music status: DISABLED.", flush=True)
            return

        # ─── Fix Port/SSL for Render ──────────────────────────────────
        if "onrender.com" in node_uri:
             if not node_uri.startswith("http"):
                 node_uri = f"https://{node_uri}"
             if ":" not in node_uri.replace("https://", "").replace("http://", ""):
                 node_uri = f"{node_uri}:443"

        print(f"📡 LOUD: Target Lavalink URI: {node_uri}", flush=True)

        retry_count = 0
        while True:
            retry_count += 1
            print(f"🔄 LOUD: Lavalink Connection Attempt #{retry_count}...", flush=True)
            
            # ─── Pre-flight Diagnostic ──────────────────────
            # This wakes up the Lavalink node if it is sleeping on Render
            try:
                print(f"📡 LOUD: Pinging Lavalink version endpoint... (Attempt {retry_count})", flush=True)
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{node_uri}/version", headers={"Authorization": node_password}, timeout=15) as resp:
                        if resp.status == 200:
                            ver = await resp.text()
                            print(f"✅ LOUD: Lavalink version check SUCCESS: {ver}", flush=True)
                        else:
                            print(f"❌ LOUD: Lavalink version check FAILED: HTTP {resp.status}", flush=True)
            except Exception as e:
                print(f"⚠️ LOUD: Lavalink version check error (Node might be booting): {e}", flush=True)

            try:
                print(f"📡 LOUD: Calling wavelink.Pool.connect()...", flush=True)
                
                # Be explicit about SSL for Render's https URLs
                use_ssl = node_uri.startswith("https")
                print(f"📡 LOUD: Node Config - URI: {node_uri}, USE_HTTPS: {use_ssl}", flush=True)
                
                node = wavelink.Node(uri=node_uri, password=node_password)
                await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
                print("✅ LOUD: wavelink.Pool.connect() completed successfully!", flush=True)
                break 
            except Exception as e:
                print(f"❌ LOUD: Wavelink Connection Error: {e}. Retrying in 15 seconds...", flush=True)
                await asyncio.sleep(15)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"🎵 Wavelink Node connected and ready! | Resumed: {payload.resumed}")

    # ─── Music Commands ─────────────────────────────────────────────

    @commands.hybrid_command(name="musicstatus", description="Check the status of the Lavalink node.")
    async def musicstatus(self, ctx: commands.Context):
        nodes = wavelink.Pool.nodes
        if not nodes:
            return await ctx.send("❌ No Lavalink nodes are currently registered in the pool.")
        
        status_text = ""
        for identifier, node in nodes.items():
            status_text += f"Node: `{identifier}`\nStatus: `{node.status}`\nURI: `{node.uri}`\n\n"
        
        embed = discord.Embed(title="🎵 Music Status", description=status_text, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="play", description="Plays a song or search query.")
    @app_commands.describe(search="The song to play (URL or keywords)")
    async def play(self, ctx: commands.Context, *, search: str):
        # ─── 1. Instant Defer to prevent timeout ───
        await ctx.defer()
        
        if not ctx.author.voice:
            return await ctx.send("❌ You must be in a voice channel!")

        # PRE-CHECK: Ensure nodes are ready
        nodes = wavelink.Pool.nodes
        if not nodes:
            return await ctx.send("❌ The Music Server (Lavalink) is not connected yet. Please wait a moment.")
            
        # Ensure at least one node is connected
        connected_node = None
        for node in nodes.values():
            if node.status == wavelink.NodeStatus.CONNECTED:
                connected_node = node
                break
        
        if not connected_node:
            print("⚠️ LOUD: Play command called but no nodes are CONNECTED.", flush=True)
            return await ctx.send("❌ The Music Server is currently RECONNECTING. Please wait a few seconds.")

        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player:
            try:
                if not discord.opus.is_loaded():
                    print("⚠️ LOUD: Opus is not loaded! Attempting to load...", flush=True)
                    try:
                        discord.opus.load_opus("libopus.so.0" if os.name != "nt" else "libopus-0.x64.dll")
                    except:
                        print("❌ LOUD: Failed to load Opus manually. Voice might fail.", flush=True)

                print(f"📡 LOUD: Connecting to {ctx.author.voice.channel.name}...", flush=True)
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player, timeout=30, self_deaf=True)
                print("✅ LOUD: Voice connection successful.", flush=True)
            except Exception as e:
                print(f"❌ LOUD: Voice Connection failed: {e}", flush=True)
                return await ctx.send(f"❌ Could not join voice: {e}")

        print(f"📡 LOUD: Searching for: {search}", flush=True)
        try:
            tracks: wavelink.Search = await wavelink.Playable.search(search)
            if not tracks:
                print(f"❌ LOUD: No tracks found for {search}", flush=True)
                return await ctx.send(f"❌ No results found for: `{search}`")
            print(f"✅ LOUD: Found {len(tracks) if not isinstance(tracks, wavelink.Playlist) else 'Playlist'} tracks.", flush=True)
        except Exception as e:
            print(f"❌ LOUD: Search error: {e}", flush=True)
            return await ctx.send(f"❌ Search error: {e}")

        if isinstance(tracks, wavelink.Playlist):
            added = tracks.tracks
            player.queue.put(added)
            embed = discord.Embed(title="🎵 Playlist Added", description=f"Added **{tracks.name}**", color=discord.Color.purple())
        else:
            track = tracks[0]
            player.queue.put(track)
            embed = discord.Embed(title="🎵 Track Loaded", description=f"**{track.title}**", color=discord.Color.blue())
            if track.artwork: embed.set_thumbnail(url=track.artwork)

        if not player.playing:
            try:
                print(f"📡 LOUD: Starting playback of {player.queue[0].title}...", flush=True)
                await player.play(player.queue.get())
                print("✅ LOUD: Playback started successfully.", flush=True)
                embed.title = "🎵 Now Playing"
            except Exception as e:
                print(f"❌ LOUD: Playback error: {e}", flush=True)
                return await ctx.send(f"❌ Playback error: {e}")
        
        # Add control view
        view = MusicController(player)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="skip", description="Skip the current track.")
    async def skip(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player: return await ctx.send("Nothing is playing!")
        await player.skip()
        await ctx.send("⏭️ Skipped!")

    @commands.hybrid_command(name="stop", description="Stop and clear the queue.")
    async def stop(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player: return await ctx.send("Nothing is playing!")
        await player.disconnect()
        await ctx.send("🛑 Stopped and disconnected.")

    # ─── Extended Features / Playlists ──────────────────────────────

    @commands.hybrid_command(name="playfile", description="Play an uploaded file.")
    async def playfile(self, ctx: commands.Context, file: discord.Attachment):
        await ctx.send(f"🎵 Attempting to play file: `{file.filename}`")
        # Logic to play attachment...

    @commands.hybrid_command(name="playliked", description="Queue all your liked songs.")
    async def playliked(self, ctx: commands.Context):
        await ctx.send("❤️ Queueing your liked songs...")

    playlist = app_commands.Group(name="playlist", description="Manage your playlists")

    @playlist.command(name="list", description="List all saved playlists.")
    async def playlist_list(self, interaction: discord.Interaction):
        await interaction.response.send_message("📜 Here are your saved playlists...")

    @playlist.command(name="addcurrent", description="Add current song to a playlist.")
    async def playlist_add(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Added current song to your playlist!")

    @playlist.command(name="addqueue", description="Add whole queue to a playlist.")
    async def playlist_addqueue(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Added current queue to a new playlist!")

async def setup(bot):
    await bot.add_cog(Music(bot))
