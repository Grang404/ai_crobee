from discord.ext import commands
import random


class RockPaperScissors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rps")
    async def rock_paper_scissors(self, ctx, choice: str = None):
        choices = ["rock", "paper", "scissors"]
        if choice.lower() not in choices:
            await ctx.send("pick rock, paper, or scissors c.c")
            return

        bot_choice = random.choice(choices)
        result = self.determine_winner(choice.lower(), bot_choice)
        await ctx.send(f"u chose {choice}, i chose {bot_choice} {result}")

    def determine_winner(self, player_choice, bot_choice):
        if player_choice == bot_choice:
            return "it a tie ;c"
        elif (
            (player_choice == "rock" and bot_choice == "scissors")
            or (player_choice == "paper" and bot_choice == "rock")
            or (player_choice == "scissors" and bot_choice == "paper")
        ):
            return "u win :catcri:"
        else:
            return "i win x.x"


# Adding a command error handler
@commands.Cog.listener()
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("pick rock, paper, or scissors c.c")
    else:
        await ctx.send("pick rock, paper, or scissors c.c")


async def setup(bot):
    await bot.add_cog(RockPaperScissors(bot))
    bot.add_listener(on_command_error)
