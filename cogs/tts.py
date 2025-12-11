import discord
from discord.ext import commands
import os
import re
from io import BytesIO
import requests
import asyncio

# TODO: Add message queue for TTS?
# TODO: Add systemd logging


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
        """Sanitise message content for TTS"""

        # Convert Discord mentions to readable names
        for mention in message.mentions:
            text = text.replace(f"<@{mention.id}>", mention.display_name)
            text = text.replace(f"<@!{mention.id}>", mention.display_name)

        for role in message.role_mentions:
            text = text.replace(f"<@&{role.id}>", role.name)

        for channel in message.channel_mentions:
            text = text.replace(f"<#{channel.id}>", f"#{channel.name}")

        # Convert markdown links [text](url) to just text (vencord emojis lmao)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)

        # Replace custom emotes with their names
        text = re.sub(r"<[a]?:([^:]+):\d+>", r"\1", text)

        # Replace @ with "at", adding spaces as needed
        text = re.sub(r"(\S)@", r"\1 at ", text)  # character before @
        text = re.sub(r"@(\S)", r"at \1", text)  # character after @
        text = text.replace("@", "at")  # standalone @

        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+",
            flags=re.UNICODE,
        )

        text = emoji_pattern.sub(r"", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text if text else ""

    def generate_elevenlabs_tts(self, text, voice_id):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key,
        }
        payload = {
            "text": text,
            "model_id": "eleven_flash_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.5,
                "use_speaker_boost": True,
            },
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.content
        else:
            print(f"TTS Generation Error: {response.status_code}::{response.text}")
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

    async def connect_direct(self, channel, retries=3, delay=2):
        for _ in range(retries):
            try:
                return await channel.connect()
            except Exception:
                await asyncio.sleep(delay)
        raise RuntimeError("Voice connect failed after retries")

    async def ensure_voice_connection(self, message):
        if not message.author.voice:
            return False

        target_channel = message.author.voice.channel
        vc = self.config.get("current_voice_client")

        if vc and vc.is_connected():
            if vc.channel == target_channel:
                return True
            await self.safe_disconnect()

        self.config["current_voice_client"] = await self.connect_direct(target_channel)
        return True

    async def play_tts_audio(self, clean_content):
        """Play TTS audio"""
        try:
            vc = self.config.get("current_voice_client")
            if not vc or not vc.is_connected():
                print("Voice client not connected, skipping TTS generation")
                return False

            # Already have a valid VC, generate TTS
            audio_content = self.generate_elevenlabs_tts(clean_content, self.voice_id)
            if not audio_content:
                print("TTS generation failed")
                return False

            # Create audio source
            audio_source = discord.FFmpegPCMAudio(BytesIO(audio_content), pipe=True)

            # Play audio if not already playing
            if not vc.is_playing():
                vc.play(audio_source)
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

        # Handle if the bot gets disconnected
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

        print(f"Error in event {event} with args {args} and kwargs {kwargs}")
        print(traceback.format_exc())
        await self.safe_disconnect()

    @commands.Cog.listener()
    async def on_message(self, message):
        if (
            self.config["target_user_id"]
            and message.author.id == self.config["target_user_id"]
        ):
            if not message.content.startswith("!") and message.content.strip():
                connection_result = await self.ensure_voice_connection(message)
                if not connection_result:
                    print(
                        f"Failed to establish voice connection for message: {message.content}"
                    )
                    return

                clean_content = self.clean_text(message.content, message)
                if clean_content:
                    print(f"{message.author.name}: {clean_content}")
                    await self.play_tts_audio(clean_content)


async def setup(bot):
    await bot.add_cog(TTSListener(bot))
