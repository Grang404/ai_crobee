import discord
from discord.ext import commands
import os
import re
from io import BytesIO
import requests


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
        for mention in message.mentions:
            text = text.replace(f"<@{mention.id}>", mention.display_name)
            text = text.replace(f"<@!{mention.id}>", mention.display_name)

        for role in message.role_mentions:
            text = text.replace(f"<@&{role.id}>", role.name)

        for channel in message.channel_mentions:
            text = text.replace(f"<#{channel.id}>", f"#{channel.name}")

        return text

    def clean_text(self, text, message):
        text = self.convert_mentions_to_names(text, message)
        text_without_urls = re.sub(r"https?://\S+", "", text)
        return re.sub(r"<:([^:]+):\d+>", r"\1", text_without_urls).strip()

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

                    audio_content = self.generate_elevenlabs_tts(
                        clean_content, self.voice_id
                    )
                    if audio_content:
                        # Creating a temp file in memory
                        audio_source = discord.FFmpegPCMAudio(
                            BytesIO(audio_content), pipe=True
                        )

                        # Play audio
                        if not self.config["current_voice_client"].is_playing():
                            self.config["current_voice_client"].play(audio_source)

                except Exception as e:
                    print(f"Comprehensive Error playing TTS: {e}")
                    import traceback

                    traceback.print_exc()

    @commands.command(name="tts")
    async def tts_command(self, ctx, *, text=None):
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

                    audio_content = self.generate_elevenlabs_tts(
                        clean_content, self.voice_id
                    )
                    if audio_content:
                        # Creating a temp file in memory
                        audio_source = discord.FFmpegPCMAudio(
                            BytesIO(audio_content), pipe=True
                        )

                        # Play audio
                        if not self.config["current_voice_client"].is_playing():
                            self.config["current_voice_client"].play(audio_source)

                except Exception as e:
                    print(f"Comprehensive Error playing TTS: {e}")
                    import traceback

                    traceback.print_exc()


async def setup(bot):
    await bot.add_cog(TTSListener(bot))
