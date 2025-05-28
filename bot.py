import os
import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.command(name='hello')
async def hello(ctx):
    """Simple hello command"""
    await ctx.send('Hello! I\'m the Pinball Map Bot!')


@client.command(name='ping')
async def ping(ctx):
    """Ping command to test bot responsiveness"""
    await ctx.send(f'Pong! Latency: {round(client.latency * 1000)}ms')


@client.command(name='machines')
async def machines(ctx):
    """List all pinball machines in Austin, TX"""
    try:
        # Fetch locations from Austin region
        response = requests.get('https://pinballmap.com/api/v1/region/austin/locations.json')
        response.raise_for_status()
        
        locations = response.json()['locations']
        
        # Count total machines and create summary
        total_machines = sum(location.get('machine_count', 0) for location in locations)
        total_locations = len(locations)
        
        message = f"**Pinball Machines in Austin, TX**\n"
        message += f"Found {total_machines} machines across {total_locations} locations\n\n"
        
        # List first few locations with machines
        for i, location in enumerate(locations[:5]):
            if location.get('machine_count', 0) > 0:
                name = location.get('name', 'Unknown')
                machine_count = location.get('machine_count', 0)
                message += f"• **{name}** - {machine_count} machine(s)\n"
        
        if len(locations) > 5:
            message += f"\n... and {len(locations) - 5} more locations"
        
        await ctx.send(message)
        
    except requests.RequestException as e:
        await ctx.send(f"Sorry, I couldn't fetch the pinball data right now. Error: {str(e)}")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
        print("Please create a .env file with your Discord bot token.")
        exit(1)

    client.run(token)
