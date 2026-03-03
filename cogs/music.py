import discord
from discord.ext import commands
import wavelink

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Provide a public node for testing. Users should replace this or host their own!
        # This is a community-run public lavalink node from lavalink.top
        nodes = [wavelink.Node(uri="http://lava.link:80", password="youshallnotpass")]
        
        # Connect to Lavalink
        await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"🎵 Wavelink Node connected: {payload.node!r} | Resumed: {payload.resumed}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return
            
        track = payload.track
        # To avoid spamming on start, we could send a message, but since Play command sends "Added to queue" or "Playing", 
        # it's usually enough. However, we'll log it here.
        print(f"🎵 Started playing: {track.title}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return

        # Play next track if queue has items
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
        else:
            # Leave channel if empty
            await player.disconnect()

    @commands.hybrid_command(name="play", help="Play a song or add it to the queue.")
    async def play(self, ctx: commands.Context, *, search: str):
        """Play a song from a search term or URL."""
        if not ctx.author.voice:
            return await ctx.send("❌ You must be in a voice channel to play music!")

        # Acknowledge the command right away avoiding discord timeouts
        await ctx.defer() 

        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        
        if not player:
            try:
                # connect the bot
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await ctx.send(f"❌ Could not connect to your voice channel: {e}")

        # Search for tracks using the lavalink node
        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if not tracks:
            return await ctx.send(f"❌ Could not find any songs with query: `{search}`")

        # Support for playlists
        if isinstance(tracks, wavelink.Playlist):
            added = tracks.tracks
            player.queue.put(added)
            embed = discord.Embed(
                title="🎵 Playlist Added to Queue", 
                description=f"Added **{tracks.name}** ({len(added)} tracks)", 
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            track = tracks[0]
            player.queue.put(track)
            embed = discord.Embed(
                title="🎵 Track Added to Queue", 
                description=f"Added **{track.title}** by {track.author}", 
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

        # Trigger play if nothing is currently playing
        if getattr(player, "playing", False) is False:
            if not player.queue.is_empty:
                await player.play(player.queue.get())

    @commands.hybrid_command(name="skip", help="Skip the currently playing song.")
    async def skip(self, ctx: commands.Context):
        """Skip the current song."""
        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player or not getattr(player, "playing", False):
            return await ctx.send("❌ I am not playing anything.")
            
        await player.skip(force=True)
        await ctx.send("⏭️ Skipped current song!")

    @commands.hybrid_command(name="stop", help="Stop playing and clear the queue.")
    async def stop(self, ctx: commands.Context):
        """Stop music, clear queue, and leave voice channel."""
        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player:
            return await ctx.send("❌ I am not connected to a voice channel.")

        player.queue.clear()
        await player.disconnect()
        await ctx.send("🛑 Stopped music and disconnected.")

    @commands.hybrid_command(name="queue", help="Show the current music queue.")
    async def queue(self, ctx: commands.Context):
        """Show the current queue."""
        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player or player.queue.is_empty:
            return await ctx.send("The queue is empty.")

        embed = discord.Embed(title="🎵 Current Queue", color=discord.Color.blue())
        for i, track in enumerate(player.queue, 1):
            embed.add_field(name=f"{i}. {track.title}", value=f"by {track.author}", inline=False)
            if i >= 10: # limit to top 10
                embed.set_footer(text=f"And {len(player.queue) - 10} more...")
                break
                
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pause", help="Pause the current song.")
    async def pause(self, ctx: commands.Context):
        """Pause the current song."""
        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player:
            return await ctx.send("❌ I am not connected to a voice channel.")
        
        await player.pause(True)
        await ctx.send("⏸️ Paused the music.")

    @commands.hybrid_command(name="resume", help="Resume the current song.")
    async def resume(self, ctx: commands.Context):
        """Resume the paused song."""
        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player:
            return await ctx.send("❌ I am not connected to a voice channel.")
            
        await player.pause(False)
        await ctx.send("▶️ Resumed the music.")

    @commands.hybrid_command(name="volume", help="Set the music player volume.")
    async def volume(self, ctx: commands.Context, volume: int):
        """Set the player volume."""
        player: wavelink.Player = getattr(ctx.guild, "voice_client", None)
        if not player:
            return await ctx.send("❌ I am not connected to a voice channel.")
            
        if not 0 <= volume <= 100:
            return await ctx.send("❌ Volume must be between 0 and 100.")
            
        await player.set_volume(volume)
        await ctx.send(f"🔊 Set volume to {volume}%")

async def setup(bot):
    await bot.add_cog(Music(bot))
