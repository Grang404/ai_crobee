import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
bot_key = os.getenv("BOT_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.start_time = datetime.now(timezone.utc)  # type: ignore[attr-defined]


@bot.event
async def on_ready():
    if bot.user is None:
        print("Error: bot user is none")
        return

    print(f"Logged in as {bot.user.name}")

    app_info = await bot.application_info()
    print(f"Owner: {app_info.owner}")

    # Load all cogs
    for filename in os.listdir("./cogs"):
        if (
            filename.endswith(".py")
            and not filename.startswith("_")
            and filename != "__init__.py"
        ):
            await bot.load_extension(f"cogs.{filename[:-3]}")

    guild = discord.Object(id=1083925119631642624)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("Commands synced")

    @bot.command()
    @commands.is_owner()
    async def reload(ctx, extension):
        """Reload a cog without restarting the bot"""
        try:
            await bot.reload_extension(f"cogs.{extension}")
            await ctx.send(f"✅ Reloaded {extension}")
        except commands.CommandError as e:
            await ctx.send(f"❌ Error: {e}")


if bot_key is None:
    raise ValueError("BOT_KEY environment variable is not set")

bot.run(bot_key)
