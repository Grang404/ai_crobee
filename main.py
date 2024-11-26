import discord
from discord.ext import commands
import os
import re
import tempfile
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()
bot_key = os.getenv("BOT_KEY")
azure_tts_key = os.getenv("AZURE_TTS_KEY")
azure_region = os.getenv("AZURE_REGION")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

config = {"target_user_id": 343414109213294594, "current_voice_client": None}


def convert_mentions_to_names(text, message):
    for mention in message.mentions:
        text = text.replace(f"<@{mention.id}>", mention.display_name)
        text = text.replace(f"<@!{mention.id}>", mention.display_name)

    for role in message.role_mentions:
        text = text.replace(f"<@&{role.id}>", role.name)

    for channel in message.channel_mentions:
        text = text.replace(f"<#{channel.id}>", f"#{channel.name}")

    return text


def clean_text(text, message):
    text = convert_mentions_to_names(text, message)
    text_without_urls = re.sub(r"https?://\S+", "", text)
    return re.sub(r"<:([^:]+):\d+>", r"\1", text_without_urls).strip()


def generate_azure_tts(text, voice_name):
    try:
        # Create a temporary file with a .wav extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            # Configure Azure Speech SDK
            speech_config = speechsdk.SpeechConfig(
                subscription=azure_tts_key, region=azure_region
            )
            speech_config.speech_synthesis_voice_name = voice_name
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
            )

            # Configure audio output to the temporary file
            audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_audio.name)

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
        return None


async def ensure_voice_connection(message):
    """Ensure the bot is connected to the correct voice channel"""
    if not message.author.voice:
        return False

    target_channel = message.author.voice.channel

    # If we're not connected at all
    if not config["current_voice_client"]:
        config["current_voice_client"] = await target_channel.connect()
        return True

    # If we're connected but in the wrong channel
    if config["current_voice_client"].channel != target_channel:
        await config["current_voice_client"].disconnect()
        config["current_voice_client"] = await target_channel.connect()
        return True

    # If we're already in the correct channel
    return True


@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes"""
    # Only care about the target user completely leaving voice
    if member.id == config["target_user_id"] and before.channel and not after.channel:
        if config["current_voice_client"]:
            await config["current_voice_client"].disconnect()
            config["current_voice_client"] = None
            print(f"Disconnected because {member.name} left voice")


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if config["target_user_id"] and message.author.id == config["target_user_id"]:
        if not message.content.startswith("!") and message.content.strip():
            try:
                # Ensure proper voice connection
                if not await ensure_voice_connection(message):
                    return

                clean_content = clean_text(message.content, message)
                print(f"TTS Message: {message.author.name}: {clean_content}")

                # Generate TTS to a temporary file
                audio_file = generate_azure_tts(
                    clean_content, "en-US-AndrewMultilingualNeural"
                )

                if audio_file:
                    # Create FFmpeg audio source from the file
                    audio_source = discord.FFmpegPCMAudio(audio_file)

                    # Play audio
                    if not config["current_voice_client"].is_playing():
                        config["current_voice_client"].play(
                            audio_source,
                            after=lambda e: (
                                os.unlink(audio_file)
                                if os.path.exists(audio_file)
                                else None
                            ),
                        )

            except Exception as e:
                print(f"Error playing TTS: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")


@bot.command()
async def set_target(ctx, user: discord.Member):
    config["target_user_id"] = user.id
    await ctx.send(f"Now listening for messages from {user.name}")


@bot.command()
async def leave(ctx):
    if config["current_voice_client"]:
        await config["current_voice_client"].disconnect()
        config["current_voice_client"] = None
        await ctx.send("Left voice channel")


bot.run(bot_key)
