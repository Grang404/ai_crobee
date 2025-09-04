import discord
from discord.ext import commands
import subprocess
import asyncio

class ZomboidServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='whoami')
    async def whoami(self, ctx):
        stdout, stderr = await self.run_command("whoami")
        await ctx.send(f"Bot running as: {stdout}")
        
        stdout2, stderr2 = await self.run_command("id")
        await ctx.send(f"Full user info: {stdout2}")

    async def run_command(self, command):
        """Run a system command and return the result"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip(), None
            else:
                return None, stderr.decode().strip()
        except Exception as e:
            return None, str(e)

    @commands.command(name='restart')
    @commands.has_permissions(administrator=True)
    async def restart_server(self, ctx):
        """Restart the Zomboid server"""
        await ctx.send("🔄 Restarting Zomboid server...")
        
        stdout, stderr = await self.run_command("sudo systemctl restart zomboid")
        
        if stderr:
            await ctx.send(f"❌ Error restarting server: {stderr}")
        else:
            await ctx.send("✅ Server restart command sent successfully!")

    @commands.command(name='start')
    @commands.has_permissions(administrator=True)
    async def start_server(self, ctx):
        """Start the Zomboid server"""
        await ctx.send("🚀 Starting Zomboid server...")
        
        stdout, stderr = await self.run_command("sudo systemctl start zomboid.socket")
        
        if stderr:
            await ctx.send(f"❌ Error starting server: {stderr}")
        else:
            await ctx.send("✅ Server start command sent successfully!")

    @commands.command(name='stop')
    @commands.has_permissions(administrator=True)
    async def stop_server(self, ctx):
        """Stop the Zomboid server"""
        await ctx.send("⏹️ Stopping Zomboid server...")
        
        stdout, stderr = await self.run_command("sudo systemctl stop zomboid")
        
        if stderr:
            await ctx.send(f"❌ Error stopping server: {stderr}")
        else:
            await ctx.send("✅ Server stopped successfully!")

    @commands.command(name='status')
    async def server_status(self, ctx):
        """Check Zomboid server status"""
        stdout, stderr = await self.run_command("sudo systemctl status zomboid --no-pager -l")
        
        if stdout:
            # Extract key information from systemctl status
            lines = stdout.split('\n')
            status_line = next((line for line in lines if 'Active:' in line), "Status unknown")
            
            if 'active (running)' in status_line.lower():
                embed = discord.Embed(title="🟢 Server Status", description="Server is running", color=0x00ff00)
            elif 'inactive' in status_line.lower():
                embed = discord.Embed(title="🔴 Server Status", description="Server is stopped", color=0xff0000)
            else:
                embed = discord.Embed(title="🟡 Server Status", description=status_line, color=0xffff00)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Error checking status: {stderr}")

    @commands.command(name='logs')
    @commands.has_permissions(administrator=True)
    async def server_logs(self, ctx, lines: int = 10):
        """Get recent server logs"""
        if lines > 50:
            lines = 50  # Limit to prevent spam
            
        stdout, stderr = await self.run_command(f"sudo journalctl -u zomboid -n {lines} --no-pager")
        
        if stdout:
            # Discord has a 2000 character limit for messages
            if len(stdout) > 1900:
                stdout = stdout[-1900:]
                stdout = "..." + stdout
            
            await ctx.send(f"```\n{stdout}\n```")
        else:
            await ctx.send(f"❌ Error getting logs: {stderr}")

    @commands.command(name='send')
    @commands.has_permissions(administrator=True)
    async def send_command(self, ctx, *, command: str):
        """Send a command to the Zomboid server"""
        stdout, stderr = await self.run_command(f'echo "{command}" | sudo tee /home/pzuser/pzserver/zomboid.control')
        
        if stderr:
            await ctx.send(f"❌ Error sending command: {stderr}")
        else:
            await ctx.send(f"📤 Command sent: `{command}`")

    @commands.command(name='save')
    @commands.has_permissions(administrator=True)
    async def save_server(self, ctx):
        """Save the server world"""
        await ctx.send("💾 Saving server...")
        
        stdout, stderr = await self.run_command('echo "save" | sudo tee /home/pzuser/pzserver/zomboid.control')
        
        if stderr:
            await ctx.send(f"❌ Error saving: {stderr}")
        else:
            await ctx.send("✅ Save command sent!")

async def setup(bot):
    await bot.add_cog(ZomboidServer(bot))
