import discord
from discord.ext import commands
import os
import re
from io import BytesIO
import requests
from dotenv import load_dotenv

load_dotenv()
bot_key = os.getenv('BOT_KEY')
elevenlabs_key = os.getenv('API_KEY')
voice_id = "0dPqNXnhg2bmxQv1WKDp"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

config = {
    'target_user_id': 343414109213294594,
    'current_voice_client': None
}

def convert_mentions_to_names(text, message):
    for mention in message.mentions:
        text = text.replace(f'<@{mention.id}>', mention.display_name)
        text = text.replace(f'<@!{mention.id}>', mention.display_name)

    for role in message.role_mentions:
        text = text.repalce(f'<@&{role.id}>', role.name)

    for channel in message.channel_mentions:
        text = text.replace(f'<#{channel.id}>', f'#{channel.name}')

    return text

def generate_elevenlabs_tts(text, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": elevenlabs_key
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.content
    else:
        print(f"TTS Generation Error: {response.text}")
        return False

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def set_target(ctx, user: discord.Member):
    config['target_user_id'] = user.id
    await ctx.send(f'Now listening for messages from {user.name}')

@bot.command()
async def leave(ctx):
    if config['current_voice_client']:
        await config['current_voice_client'].disconnect()
        config['current_voice_client'] = None
        await ctx.send('Left voice channel')

def clean_text(text, message):
    text = convert_mentions_to_names(text, message)
    text_without_urls = re.sub(r'https?://\S+', '', text)
    return re.sub(r'<:([^:]+):\d+>', r'\1', text_without_urls).strip()

async def ensure_voice_connection(message):
    """Ensure the bot is connected to the correct voice channel"""
    if not message.author.voice:
        return False
        
    target_channel = message.author.voice.channel
    
    # If we're not connected at all
    if not config['current_voice_client']:
        config['current_voice_client'] = await target_channel.connect()
        return True
        
    # If we're connected but in the wrong channel
    if config['current_voice_client'].channel != target_channel:
        await config['current_voice_client'].disconnect()
        config['current_voice_client'] = await target_channel.connect()
        return True
        
    # If we're already in the correct channel
    return True

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    
    if (config['target_user_id'] and 
        message.author.id == config['target_user_id']):
        
        if not message.content.startswith('!') and message.content.strip():
            try:
                # Ensure proper voice connection
                if not await ensure_voice_connection(message):
                    return
                
                clean_content = clean_text(message.content, message)
                print(f"TTS Message: {message.author.name}: {clean_content}")
                
                audio_content = generate_elevenlabs_tts(clean_content, voice_id)
                if audio_content:
                    # Creating a temp file in memory
                    audio_source = discord.FFmpegPCMAudio(BytesIO(audio_content), pipe=True)
                    
                    # Play audio
                    if not config['current_voice_client'].is_playing():
                        config['current_voice_client'].play(audio_source)
                
            except Exception as e:
                print(f"Error playing TTS: {e}")

bot.run(bot_key)
