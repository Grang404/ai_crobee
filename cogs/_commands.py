from discord import app_commands


@commands.command()  # ERROR HANDLING
async def set_target(self, ctx, user: discord.Member):
    self.config["target_user_id"] = user.id
    await ctx.send(f"Now listening for messages from {user.name}")


@commands.command()
async def leave(self, ctx):
    await self.safe_disconnect()
    await ctx.send("Left voice channel")
