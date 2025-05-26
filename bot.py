import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='hello')
async def hello(ctx):
    """Simple hello command"""
    await ctx.send('Hello! I\'m the Pinball Map Bot!')

@bot.command(name='ping')
async def ping(ctx):
    """Ping command to test bot responsiveness"""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
        print("Please create a .env file with your Discord bot token.")
        exit(1)
    
    bot.run(token)