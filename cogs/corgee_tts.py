import discord
from discord.ext import commands
import os
import re
import tempfile
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv


class AzureTTSListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {
            "target_user_id": 343414109213294594,
            "current_voice_client": None,
        }
        # Load Azure credentials from environment
        self.azure_tts_key = os.getenv("AZURE_TTS_KEY")
        self.azure_region = os.getenv("AZURE_REGION")
        self.voice_name = "en-US-AndrewMultilingualNeural"

    def convert_mentions_to_names(self, text, message):
        """Convert Discord mentions to display names"""
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
        return re.sub(r"<:([^:]+):\d+>", r"\1", text_without_urls).strip()

    def generate_azure_tts(self, text):
        """Generate Azure Text-to-Speech audio"""
        try:
            # Create a temporary file with a .wav extension
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                # Configure Azure Speech SDK
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.azure_tts_key, region=self.azure_region
                )
                speech_config.speech_synthesis_voice_name = self.voice_name
                speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
                )

                # Configure audio output to the temporary file
                audio_config = speechsdk.audio.AudioOutputConfig(
                    filename=temp_audio.name
                )

                # Create speech synthesizer
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config, audio_config=audio_config
                )

                # Synthesize text to file
                result = synthesizer.speak_text_async(text).get()

                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    print(f"TTS generated to {temp_audio.name}")
                    return temp_audio.name
                else:
                    print(f"TTS Generation Error: {result.reason}")
                    return None
        except Exception as e:
            print(f"Error in generate_azure_tts: {e}")
            import traceback

            traceback.print_exc()
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
        """Set the target user for TTS"""
        self.config["target_user_id"] = user.id
        await ctx.send(f"Now listening for messages from {user.name}")

    @commands.command()
    async def leave(self, ctx):
        """Make the bot leave the current voice channel"""
        if self.config["current_voice_client"]:
            await self.config["current_voice_client"].disconnect()
            self.config["current_voice_client"] = None
            await ctx.send("Left voice channel")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes"""
        # Only care about the target user completely leaving voice
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
                    audio_file = self.generate_azure_tts(clean_content)

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

    @commands.command(name="tts")
    async def tts_command(self, ctx, *, text=None):
        """Custom TTS command for a specific user"""
        if ctx.author.id == 148749538373402634:
            if text and not text.startswith("!"):
                try:
                    # Ensure proper voice connection
                    connection_result = await self.ensure_voice_connection(ctx.message)
                    if not connection_result:
                        print(
                            f"Failed to establish voice connection for message: {text}"
                        )
                        return

                    clean_content = self.clean_text(text, ctx.message)
                    print(f"TTS Message: {ctx.author.name}: {clean_content}")

                    # Generate TTS to a temporary file
                    audio_file = self.generate_azure_tts(clean_content)

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
    await bot.add_cog(AzureTTSListener(bot))
