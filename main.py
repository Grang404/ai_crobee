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
user_id = os.getenv('USER_ID')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

config = {
    'target_user_id': 148749538373402634,
    'current_voice_client': None
}

def generate_elevenlabs_tts(text, user_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{user_id}"
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

def clean_text(text):
   text_without_urls = re.sub(r'https?://\S+', '', text)
   return re.sub(r'<:([^:]+):\d+>', r'\1', text_without_urls).strip()

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    
    if (config['target_user_id'] and 
        message.author.id == config['target_user_id']):
        
        if not message.content.startswith('!') and message.content.strip():
            try:
                # Check if the user is in a voice channel
                if message.author.voice and message.author.voice.channel:
                    # Disconnect existing voice client if connected to a different channel
                    if config['current_voice_client']:
                        await config['current_voice_client'].disconnect()
                    
                    # Connect to the user's current voice channel
                    config['current_voice_client'] = await message.author.voice.channel.connect()
                
                clean_content = clean_text(message.content)
                
                print(f"TTS Message: {message.author.name}: {clean_content}")
                
                audio_content = generate_elevenlabs_tts(clean_content, user_id)
                if audio_content:
                    # Creating a temp file in memory
                    audio_source = discord.FFmpegPCMAudio(BytesIO(audio_content), pipe=True)
                    
                    # Play audio
                    config['current_voice_client'].play(audio_source)
                
            except Exception as e:
                print(f"Error playing TTS: {e}")

bot.run(bot_key)

