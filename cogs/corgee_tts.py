import discord
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
        self.config = {
            "target_user_id": 343414109213294594,
            "current_voice_client": None,
        }
        self.voice_id = "0dPqNXnhg2bmxQv1WKDp"
        self.elevenlabs_key = os.getenv("API_KEY")

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
        if "<a:cat_stare:999561526899900446>" in text_without_urls:
            return re.sub(r"<:([^:]+):\d+>", r"\1", text_without_urls).strip()
        else:
            return re.sub(r"<[a]?:([^:]+):\d+>", r"\1", text_without_urls).strip()

    def generate_elevenlabs_tts(self, text, voice_id):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key,
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.content
        else:
            print(f"TTS Generation Error: {response.text}")
            return False

    async def safe_disconnect(self):
        """Safely disconnect from voice channel"""
        if self.config["current_voice_client"]:
            try:
                if self.config["current_voice_client"].is_connected():
                    await self.config["current_voice_client"].disconnect()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.config["current_voice_client"] = None

    async def connect_with_retry(self, channel, max_retries=3):
        """Connect to voice channel with retry logic for 4006 errors"""
        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to {channel.name} (attempt {attempt + 1})")
                
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
                print(f"Unexpected error on attempt {attempt + 1}: {type(e).__name__}: {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise Exception(f"Failed to connect to {channel.name} after {max_retries} attempts")

    async def ensure_voice_connection(self, message):
        """Ensure the bot is connected to the correct voice channel with improved error handling"""
        if not message.author.voice:
            print("Author not in a voice channel")
            return False

        target_channel = message.author.voice.channel

        try:
            # Check if we have a valid connection to the right channel
            if (self.config["current_voice_client"] and 
                self.config["current_voice_client"].is_connected() and
                self.config["current_voice_client"].channel == target_channel):
                # Double-check the connection is actually working
                try:
                    # Test the connection by checking if we can access channel info
                    _ = self.config["current_voice_client"].channel.name
                    return True
                except:
                    print("Connection appears invalid, reconnecting...")
                    await self.safe_disconnect()

            # If we're connected to a different channel, disconnect first
            if (self.config["current_voice_client"] and 
                self.config["current_voice_client"].is_connected() and
                self.config["current_voice_client"].channel != target_channel):
                print(f"Moving from {self.config['current_voice_client'].channel.name} to {target_channel.name}")
                await self.safe_disconnect()
                # Add a brief delay after disconnect
                await asyncio.sleep(1)

            # Clean up any existing connection that's not working
            if self.config["current_voice_client"] and not self.config["current_voice_client"].is_connected():
                await self.safe_disconnect()

            # Connect with retry logic
            self.config["current_voice_client"] = await self.connect_with_retry(target_channel)
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
        if (member == self.bot.user and 
            before.channel and 
            not after.channel and 
            self.config["current_voice_client"]):
            print("Bot was disconnected from voice channel")
            self.config["current_voice_client"] = None

    @commands.Cog.listener() 
    async def on_error(self, event, *args, **kwargs):
        """Global error handler for connection issues"""
        import traceback
        error_info = traceback.format_exc()
        
        if "4006" in error_info or "ConnectionClosed" in error_info:
            print(f"Caught ConnectionClosed error in {event}: cleaning up voice connection")
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
            if not (self.config["current_voice_client"] and 
                   self.config["current_voice_client"].is_connected()):
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

    @commands.Cog.listener()
    async def on_message(self, message):
        if (
            self.config["target_user_id"]
            and message.author.id == self.config["target_user_id"]
        ):
            if not message.content.startswith("!") and message.content.strip():
                # Ensure proper voice connection
                connection_result = await self.ensure_voice_connection(message)
                if not connection_result:
                    print(f"Failed to establish voice connection for message: {message.content}")
                    return

                clean_content = self.clean_text(message.content, message)
                print(f"TTS Message: {message.author.name}: {clean_content}")

                await self.play_tts_audio(clean_content, message.author)

    @commands.command(name="tts")
    async def tts_command(self, ctx, *, text=None):
        if ctx.author.id == 148749538373402634:
            if text and not text.startswith("!"):
                # Ensure proper voice connection
                connection_result = await self.ensure_voice_connection(ctx.message)
                if not connection_result:
                    print(f"Failed to establish voice connection for message: {text}")
                    return

                clean_content = self.clean_text(text, ctx.message)
                print(f"TTS Message: {ctx.author.name}: {clean_content}")

                await self.play_tts_audio(clean_content, ctx.author)


async def setup(bot):
    await bot.add_cog(TTSListener(bot))
