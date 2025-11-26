import discord
from discord import app_commands
from discord.ext import commands


class TTSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_tts_listener(self):
        """Helper to get the TTSListener cog"""
        return self.bot.get_cog("TTSListener")

    @app_commands.command(
        name="tts_join", description="Join your voice channel for TTS"
    )
    async def join(self, interaction: discord.Interaction):
        """Manually join a voice channel"""
        # Check if in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                "[!] This command can only be used in a server!", ephemeral=True
            )
            return
        # Get Member object instead of User
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            await interaction.response.send_message(
                "[!] You're not in a voice channel!", ephemeral=True
            )
            return
        tts_listener = self.get_tts_listener()
        if not tts_listener:
            await interaction.response.send_message(
                "[!] TTS system not loaded!", ephemeral=True
            )
            return
        channel = member.voice.channel
        try:
            if tts_listener.config["current_voice_client"]:
                await tts_listener.safe_disconnect()
            tts_listener.config["current_voice_client"] = (
                await tts_listener.connect_direct(channel)
            )
            await interaction.response.send_message(
                f"[+] Joined {channel.name}", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"[!] Failed to join: {e}", ephemeral=True
            )

    @app_commands.command(name="tts_leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Manually leave the voice channel"""
        tts_listener = self.get_tts_listener()
        if not tts_listener:
            await interaction.response.send_message(
                "[!] TTS system is cooked!!", ephemeral=True
            )
            return

        if (
            tts_listener.config["current_voice_client"]
            and tts_listener.config["current_voice_client"].is_connected()
        ):
            await tts_listener.safe_disconnect()
            await interaction.response.send_message(
                "[+] Left the voice channel", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "[!] I'm not in a voice channel!", ephemeral=True
            )

    @app_commands.command(name="tts_test", description="Test TTS with a message")
    async def test(self, interaction: discord.Interaction, text: str):
        """Test TTS functionality"""
        if not interaction.guild:
            await interaction.response.send_message(
                "[!] This command can only be used in a server!", ephemeral=True
            )
            return

        # Defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        member = interaction.guild.get_member(interaction.user.id)
        tts_listener = self.get_tts_listener()
        if not tts_listener:
            await interaction.followup.send(
                "[!] TTS system not loaded!", ephemeral=True
            )
            return
        if not member or not member.voice or not member.voice.channel:
            await interaction.followup.send(
                "[!] You need to be in a voice channel!", ephemeral=True
            )
            return
        # Ensure connected
        if not tts_listener.config["current_voice_client"]:
            try:
                channel = member.voice.channel
                tts_listener.config["current_voice_client"] = (
                    await tts_listener.connect_direct(channel)
                )
            except Exception as e:
                await interaction.followup.send(
                    f"[!] Failed to connect: {e}", ephemeral=True
                )
                return

        result = await tts_listener.play_tts_audio(text)
        if result:
            await interaction.followup.send("[+] TTS test successful!", ephemeral=True)
        else:
            await interaction.followup.send("[!] TTS test failed!", ephemeral=True)

    @app_commands.command(
        name="tts_status", description="Show bot information and status"
    )
    async def status(self, interaction: discord.Interaction):
        """Display bot uptime, latency, and server information"""
        import psutil
        from datetime import datetime, timezone

        # Bot latency
        latency_ms = round(self.bot.latency * 1000, 2)

        # Bot uptime (requires storing start time in bot)
        if hasattr(self.bot, "start_time"):
            uptime_delta = datetime.now(timezone.utc) - self.bot.start_time
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            uptime_str = "Unknown (start time not tracked)"

        # Memory usage
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB

        # Create embed
        embed = discord.Embed(
            title="Status",
            color=discord.Color.green() if latency_ms < 200 else discord.Color.orange(),
        )
        embed.add_field(name="Latency", value=f"{latency_ms}ms", inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(
            name="Memory Usage", value=f"{memory_usage:.2f} MB", inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TTSCommands(bot))
