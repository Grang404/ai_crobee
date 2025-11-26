import discord
from discord import app_commands
from discord.ext import commands
import os
import re
from io import BytesIO
import requests
import asyncio
from discord.errors import ConnectionClosed


class TTSListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        target_user = os.getenv("TARGET_USER")
        self.config = {
            "target_user_id": int(target_user) if target_user else None,
            "current_voice_client": None,
        }
        self.voice_id = os.getenv("VOICE_ID")
        self.elevenlabs_key = os.getenv("API_KEY")

    def clean_text(self, text, message):
        """Convert Discord mentions to display names"""
        for mention in message.mentions:
            text = text.replace(f"<@{mention.id}>", mention.display_name)
            text = text.replace(f"<@!{mention.id}>", mention.display_name)
        for role in message.role_mentions:
            text = text.replace(f"<@&{role.id}>", role.name)
        for channel in message.channel_mentions:
            text = text.replace(f"<#{channel.id}>", f"#{channel.name}")

        # Replace @ with "at", adding spaces as needed
        # Check if there's a non-space character before @
        text = re.sub(r"(\S)@", r"\1 at ", text)
        # Check if there's a non-space character after @ (and @ wasn't already replaced)
        text = re.sub(r"@(\S)", r"at \1", text)
        # Handle standalone @ (surrounded by spaces or at edges)
        text = text.replace("@", "at")
        # Convert markdown links [text](url) to just text
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"<[a]?:([^:]+):\d+>", r"\1", text).strip()

        if not text:
            return None

        return text

    def generate_elevenlabs_tts(self, text, voice_id):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key,
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.content
        else:
            print(f"TTS Generation Error: {response.text}")
            return False

    async def safe_disconnect(self):
        if self.config["current_voice_client"]:
            try:
                if self.config["current_voice_client"].is_connected():
                    await self.config["current_voice_client"].disconnect()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.config["current_voice_client"] = None
                self._last_disconnect = asyncio.get_event_loop().time()

    async def connect_with_retry(self, channel, max_retries=3):
        """Connect to voice channel with retry logic for 4006 errors"""
        for attempt in range(max_retries):
            try:
                print(
                    f"Attempting to connect to {channel.name} (attempt {attempt + 1})"
                )

                # Add a small delay before each attempt to avoid rapid reconnections
                if attempt > 0:
                    await asyncio.sleep(min(2 ** (attempt - 1), 10))

                voice_client = await asyncio.wait_for(channel.connect(), timeout=30.0)
                print(f"Successfully connected to {channel.name}")

                # Verify connection is actually stable
                await asyncio.sleep(0.5)  # Brief pause to let connection stabilize
                if voice_client.is_connected():
                    return voice_client
                else:
                    print("Connection appeared successful but client is not connected")
                    continue

            except asyncio.TimeoutError:
                print(f"Connection timeout on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise Exception("Connection timed out after all retry attempts")

            except ConnectionClosed as e:
                print(f"ConnectionClosed error (attempt {attempt + 1}): Code {e.code}")
                if e.code == 4006:  # Session no longer valid
                    print("Session invalid, will retry...")
                    # Force a longer delay for 4006 errors
                    if attempt < max_retries - 1:
                        await asyncio.sleep(3 + attempt * 2)
                elif e.code in [4014, 4015]:  # Disconnected or voice server crashed
                    print("Voice server issue, will retry...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 + attempt)
                else:
                    print(f"Unhandled connection close code: {e.code}")
                    if attempt == max_retries - 1:
                        raise

            except discord.errors.ClientException as e:
                if "already connected to a voice channel" in str(e).lower():
                    print("Already connected error, cleaning up...")
                    # Try to clean up any existing connections
                    if self.config["current_voice_client"]:
                        try:
                            await self.config["current_voice_client"].disconnect()
                        except:
                            pass
                        self.config["current_voice_client"] = None
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                else:
                    print(f"ClientException on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        raise

            except Exception as e:
                print(
                    f"Unexpected error on attempt {attempt + 1}: {type(e).__name__}: {e}"
                )
                if attempt == max_retries - 1:
                    raise

        raise Exception(
            f"Failed to connect to {channel.name} after {max_retries} attempts"
        )

    async def ensure_voice_connection(self, message):
        """Ensure the bot is connected to the correct voice channel with improved error handling"""
        if not message.author.voice:
            print("Author not in a voice channel")
            return False

        now = asyncio.get_event_loop().time()
        if now - getattr(self, "_last_disconnect", 0) < 5:
            await asyncio.sleep(5)
        target_channel = message.author.voice.channel

        try:
            # Check if we have a valid connection to the right channel
            if (
                self.config["current_voice_client"]
                and self.config["current_voice_client"].is_connected()
                and self.config["current_voice_client"].channel == target_channel
            ):
                # Double-check the connection is actually working
                try:
                    # Test the connection by checking if we can access channel info
                    _ = self.config["current_voice_client"].channel.name
                    return True
                except:
                    print("Connection appears invalid, reconnecting...")
                    await self.safe_disconnect()

            # If we're connected to a different channel, disconnect first
            if (
                self.config["current_voice_client"]
                and self.config["current_voice_client"].is_connected()
                and self.config["current_voice_client"].channel != target_channel
            ):
                print(
                    f'Moving from {self.config["current_voice_client"].channel.name} to {target_channel.name}'
                )
                await self.safe_disconnect()
                # Add a brief delay after disconnect
                await asyncio.sleep(1)

            # Clean up any existing connection that's not working
            if (
                self.config["current_voice_client"]
                and not self.config["current_voice_client"].is_connected()
            ):
                await self.safe_disconnect()

            # Connect with retry logic
            self.config["current_voice_client"] = await self.connect_with_retry(
                target_channel
            )
            return True

        except ConnectionClosed as e:
            print(f"Voice connection failed with ConnectionClosed: {e.code} - {e}")
            await self.safe_disconnect()
            return False
        except Exception as e:
            print(f"Voice connection error: {type(e).__name__}: {e}")
            await self.safe_disconnect()
            return False

    @commands.command()
    async def set_target(self, ctx, user: discord.Member):
        self.config["target_user_id"] = user.id
        await ctx.send(f"Now listening for messages from {user.name}")

    @commands.command()
    async def leave(self, ctx):
        await self.safe_disconnect()
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
            await self.safe_disconnect()
            print(f"Disconnected because {member.name} left voice")

        # Also handle if the bot gets disconnected
        if (
            member == self.bot.user
            and before.channel
            and not after.channel
            and self.config["current_voice_client"]
        ):
            print("Bot was disconnected from voice channel")
            self.config["current_voice_client"] = None

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """Global error handler for connection issues"""
        import traceback

        error_info = traceback.format_exc()

        if "4006" in error_info or "ConnectionClosed" in error_info:
            print(
                f"Caught ConnectionClosed error in {event}: cleaning up voice connection"
            )
            await self.safe_disconnect()

        print(f"Error in {event}: {error_info}")

    async def play_tts_audio(self, clean_content, message_author):
        """Play TTS audio with error handling"""
        try:
            audio_content = self.generate_elevenlabs_tts(clean_content, self.voice_id)
            if not audio_content:
                print("Failed to generate TTS audio")
                return False

            # Check if voice client is still valid before playing
            if not (
                self.config["current_voice_client"]
                and self.config["current_voice_client"].is_connected()
            ):
                print("Voice client disconnected before playing audio")
                return False

            # Create audio source
            audio_source = discord.FFmpegPCMAudio(BytesIO(audio_content), pipe=True)

            # Play audio if not already playing
            if not self.config["current_voice_client"].is_playing():
                self.config["current_voice_client"].play(audio_source)
                return True
            else:
                print("Audio is already playing, skipping")
                return False

        except Exception as e:
            print(f"Error playing TTS audio: {e}")
            import traceback

            traceback.print_exc()
            return False

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Pong! {round(self.bot.latency * 1000)}ms"
        )

    @app_commands.command(name="say", description="Make the bot say something")
    async def say(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(message)

    @commands.Cog.listener()
    async def on_message(self, message):
        print("Received message.\nChecking ID...")
        if (
            self.config["target_user_id"]
            and message.author.id == self.config["target_user_id"]
        ):
            print("ID check passed.")
            print("Checking message not command...")
            if not message.content.startswith("!") and message.content.strip():
                print("Message valid.")
                connection_result = await self.ensure_voice_connection(message)
                if not connection_result:
                    print(
                        f"Failed to establish voice connection for message: {message.content}"
                    )
                    return
                print("Processing message into speech...")
                print(f"Message: {message.content}")
                clean_content = self.clean_text(message.content, message)
                print(f"{message.author.name}: {clean_content}")
                await self.play_tts_audio(clean_content, message.author)
                print("Speech finished.")


async def setup(bot):
    await bot.add_cog(TTSListener(bot))
