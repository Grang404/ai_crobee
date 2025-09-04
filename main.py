import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
bot_key = os.getenv("BOT_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

    # Dynamically load all cogs
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")


bot.run(bot_key)
