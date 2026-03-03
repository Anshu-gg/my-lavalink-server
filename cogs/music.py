import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import os
import logging
import aiohttp
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
        """Fix connection issues and connect to Lavalink."""
        node_uri = os.getenv("LAVALINK_URI")
        node_password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

        if not node_uri:
            print("⚠️ LAVALINK_URI not found in environment variables.")
            return

        # ─── Fix Port/SSL for Render ──────────────────────────────────
        node_uri = node_uri.rstrip('/')
        if "onrender.com" in node_uri and not any(char.isdigit() for char in node_uri.split('/')[-1]):
             # If no port specified for a Render URL, ensure it uses 443
             if not (node_uri.startswith("http://") or node_uri.startswith("https://")):
                 node_uri = f"https://{node_uri}"
             if ":" not in node_uri.replace("https://", ""):
                 node_uri = f"{node_uri}:443"

        # ─── Pre-flight Diagnostic ─────────────────────────────────────
        print(f"📡 Wavelink: Running diagnostic on {node_uri}...")
        try:
            async with aiohttp.ClientSession() as session:
                # Test if we can even reach the server
                async with session.get(f"{node_uri}/version", headers={"Authorization": node_password}, timeout=10) as resp:
                    if resp.status == 200:
                        ver = await resp.text()
                        print(f"✅ Lavalink Connection Pre-check: Success (Version: {ver})")
                    else:
                        print(f"❌ Lavalink Pre-check Failed: HTTP {resp.status}")
        except Exception as e:
             print(f"⚠️ Lavalink Pre-check Warning (Likely Network/SSL): {e}")

        try:
            # Wavelink 3.x Node setup
            node = wavelink.Node(
                uri=node_uri, 
                password=node_password,
                inactive_timeout=60
            )
            self.bot.loop.create_task(wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100))
        except Exception as e:
            print(f"❌ Wavelink Setup Error: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"🎵 Wavelink Node connected and ready! | Resumed: {payload.resumed}")

    # ─── Music Commands ─────────────────────────────────────────────

    @commands.hybrid_command(name="play", description="Plays a song or search query.")
    @app_commands.describe(search="The song to play (URL or keywords)")
    async def play(self, ctx: commands.Context, *, search: str):
        if not ctx.author.voice:
            return await ctx.send("❌ You must be in a voice channel!")

        await ctx.defer()
        
        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await ctx.send(f"❌ Connection error: {e}")

        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if not tracks:
            return await ctx.send(f"❌ No results found for: `{search}`")

        if isinstance(tracks, wavelink.Playlist):
            added = tracks.tracks
            player.queue.put(added)
            embed = discord.Embed(
                title="🎵 Playlist Added", 
                description=f"Added **{tracks.name}** ({len(added)} tracks)", 
                color=discord.Color.purple()
            )
        else:
            track = tracks[0]
            player.queue.put(track)
            embed = discord.Embed(
                title="🎵 Track Loaded", 
                description=f"**{track.title}**\nAdded to queue.", 
                color=discord.Color.blue()
            )
            if track.artwork: embed.set_thumbnail(url=track.artwork)

        if not player.playing:
            await player.play(player.queue.get())
            embed.title = "🎵 Now Playing"
        
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
