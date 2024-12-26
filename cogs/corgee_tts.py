import discord
from discord.ext import commands
import os
import re
from io import BytesIO
import pyttsx3
import tempfile
import subprocess


class TTSListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {
            "target_user_id": 148749538373402634,
            "current_voice_client": None,
        }
        # Initialize pyttsx3
        self.engine = pyttsx3.init()
        # Configure voice settings
        self.engine.setProperty("rate", 175)  # Speed of speech
        self.engine.setProperty("volume", 1.0)  # Volume level

        # Get available voices and set to first one
        voices = self.engine.getProperty("voices")
        if voices:
            self.engine.setProperty("voice", voices[0].id)

    def convert_mentions_to_names(self, text, message):
        for mention in message.mentions:
            text = text.replace(f"<@{mention.id}>", mention.display_name)
            text = text.replace(f"<@!{mention.id}>", mention.display_name)

        for role in message.role_mentions:
            text = text.replace(f"<@&{role.id}>", role.name)

        for channel in message.channel_mentions:
            text = text.replace(f"<#{channel.id}>", f"#{channel.name}")

        return text

    def clean_text(self, text, message):
        """Clean text by removing mentions, URLs, and custom emotes"""
        text = self.convert_mentions_to_names(text, message)
        text_without_urls = re.sub(r"https?://\S+", "", text)
        if "<a:cat_stare:999561526899900446>" in text_without_urls:
            return re.sub(r"<:([^:]+):\d+>", r"\1", text_without_urls).strip()
        else:
            return re.sub(r"<[a]?:([^:]+):\d+>", r"\1", text_without_urls).strip()

    def generate_tts_audio(self, text):
        """Generate TTS audio using pyttsx3 and return WAV file"""
        try:
            # Initialize pyttsx3 engine
            engine = pyttsx3.init()

            # Check available voices
            voices = engine.getProperty("voices")
            if not voices:
                print("No voices available")
                return None
            print(f"Available voices: {[voice.name for voice in voices]}")

            # Select a voice (optional)
            engine.setProperty(
                "voice", voices[0].id
            )  # Set to the first available voice

            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                wav_path = temp_wav.name
                print(f"Temporary WAV path: {wav_path}")

                # Generate the WAV file using pyttsx3
                engine.save_to_file(text, wav_path)
                engine.runAndWait()

            # Check if the file is empty
            if os.path.getsize(wav_path) == 0:
                print("Generated WAV file is empty!")
                return None

            print(f"Generated WAV file successfully at: {wav_path}")
            return wav_path

        except Exception as e:
            print(f"Error generating TTS audio: {e}")
            return None

    async def ensure_voice_connection(self, message):
        """Ensure the bot is connected to the correct voice channel"""
        if not message.author.voice:
            print("Author not in a voice channel")
            return False

        target_channel = message.author.voice.channel

        try:
            # If we're not connected at all
            if not self.config["current_voice_client"]:
                self.config["current_voice_client"] = await target_channel.connect()
                return True

            # If we're connected but in the wrong channel
            if self.config["current_voice_client"].channel != target_channel:
                await self.config["current_voice_client"].disconnect()
                self.config["current_voice_client"] = await target_channel.connect()
                return True

            # Verify the connection is still valid
            if not self.config["current_voice_client"].is_connected():
                self.config["current_voice_client"] = await target_channel.connect()
                return True

            # If we're already in the correct channel
            return True
        except Exception as e:
            print(f"Voice connection error: {e}")
            return False

    @commands.command()
    async def set_target(self, ctx, user: discord.Member):
        self.config["target_user_id"] = user.id
        await ctx.send(f"Now listening for messages from {user.name}")

    @commands.command()
    async def leave(self, ctx):
        if self.config["current_voice_client"]:
            await self.config["current_voice_client"].disconnect()
            self.config["current_voice_client"] = None
            await ctx.send("Left voice channel")

    @commands.command()
    async def voice_speed(self, ctx, speed: int):
        """Change the speech rate (words per minute). Default is 175."""
        if 50 <= speed <= 300:
            self.engine.setProperty("rate", speed)
            await ctx.send(f"Voice speed set to {speed}")
        else:
            await ctx.send("Speed must be between 50 and 300")

    @commands.command()
    async def list_voices(self, ctx):
        """List available voices"""
        voices = self.engine.getProperty("voices")
        voice_list = [f"{i}: {voice.name}" for i, voice in enumerate(voices)]
        await ctx.send("Available voices:\n" + "\n".join(voice_list))

    @commands.command()
    async def set_voice(self, ctx, voice_index: int):
        """Set the voice by index"""
        voices = self.engine.getProperty("voices")
        if 0 <= voice_index < len(voices):
            self.engine.setProperty("voice", voices[voice_index].id)
            await ctx.send(f"Voice set to: {voices[voice_index].name}")
        else:
            await ctx.send(
                "Invalid voice index. Use !list_voices to see available voices."
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes"""
        if (
            member.id == self.config["target_user_id"]
            and before.channel
            and not after.channel
        ):
            if self.config["current_voice_client"]:
                await self.config["current_voice_client"].disconnect()
                self.config["current_voice_client"] = None
                print(f"Disconnected because {member.name} left voice")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages for the target user"""
        if (
            self.config["target_user_id"]
            and message.author.id == self.config["target_user_id"]
        ):
            if not message.content.startswith("!") and message.content.strip():
                try:
                    # Ensure proper voice connection
                    connection_result = await self.ensure_voice_connection(message)
                    if not connection_result:
                        print(
                            f"Failed to establish voice connection for message: {message.content}"
                        )
                        return

                    clean_content = self.clean_text(message.content, message)
                    print(f"TTS Message: {message.author.name}: {clean_content}")

                    # Generate TTS to a temporary file
                    audio_file = self.generate_tts_audio(clean_content)

                    if audio_file:
                        # Create FFmpeg audio source from the file
                        audio_source = discord.FFmpegPCMAudio(audio_file)

                        # Play audio
                        if not self.config["current_voice_client"].is_playing():
                            self.config["current_voice_client"].play(
                                audio_source,
                                after=lambda e: (
                                    os.unlink(audio_file)
                                    if os.path.exists(audio_file)
                                    else None
                                ),
                            )

                except Exception as e:
                    print(f"Comprehensive Error playing TTS: {e}")
                    import traceback

                    traceback.print_exc()


async def setup(bot):
    await bot.add_cog(TTSListener(bot))
