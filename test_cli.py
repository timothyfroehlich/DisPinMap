#!/usr/bin/env python3
"""
CLI Test Script for Pinball Bot Commands
Simulates Discord bot commands for testing without running the full Discord bot
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import Database
from commands import CommandHandler

# Test channel ID
TEST_CHANNEL_ID = 999999999
TEST_GUILD_ID = 888888888

class MockContext:
    """Mock Discord context for testing"""
    def __init__(self, channel_id=TEST_CHANNEL_ID, guild_id=TEST_GUILD_ID):
        self.channel = MockChannel(channel_id)
        self.guild = MockGuild(guild_id)
    
    async def send(self, message):
        print(f"📤 Bot Response: {message}")

class MockChannel:
    def __init__(self, channel_id):
        self.id = channel_id

class MockGuild:
    def __init__(self, guild_id):
        self.id = guild_id

class CLITester:
    def __init__(self):
        self.db = Database("test_pinball_bot.db")
        self.command_handler = CommandHandler(self.db)
        print("🤖 CLI Test Mode - Pinball Bot Commands")
        print("Available commands:")
        print("  latlong add <lat> <lon> <radius>")
        print("  latlong remove <lat> <lon>")
        print("  location add <id_or_name>")
        print("  location remove <id>")
        print("  status")
        print("  check")
        print("  quit")
        print()

    async def process_command(self, command_line):
        """Process a command line input"""
        parts = command_line.strip().split()
        if not parts:
            return
        
        ctx = MockContext()
        
        try:
            if parts[0] == "latlong":
                await self._handle_latlong(ctx, parts[1:])
            elif parts[0] == "location":
                await self._handle_location(ctx, parts[1:])
            elif parts[0] == "status":
                await self.command_handler.handle_status(ctx)
            elif parts[0] == "check":
                await self.command_handler.handle_check(ctx)
            elif parts[0] in ["quit", "exit"]:
                return False
            else:
                print(f"❌ Unknown command: {parts[0]}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        return True

    async def _handle_latlong(self, ctx, args):
        """Handle latlong commands"""
        if not args:
            await self.command_handler.handle_latlong_list(ctx)
            return
            
        if args[0] == "add" and len(args) >= 4:
            try:
                lat, lon, radius = float(args[1]), float(args[2]), int(args[3])
                await self.command_handler.handle_latlong_add(ctx, lat, lon, radius)
            except ValueError:
                print("❌ Invalid coordinates or radius format")
        elif args[0] == "remove" and len(args) >= 3:
            try:
                lat, lon = float(args[1]), float(args[2])
                await self.command_handler.handle_latlong_remove(ctx, lat, lon)
            except ValueError:
                print("❌ Invalid coordinates format")
        else:
            print("❌ Usage: latlong add <lat> <lon> <radius> OR latlong remove <lat> <lon>")

    async def _handle_location(self, ctx, args):
        """Handle location commands"""
        if not args:
            await self.command_handler.handle_location_list(ctx)
            return
            
        if args[0] == "add" and len(args) >= 2:
            location_input = " ".join(args[1:])
            await self.command_handler.handle_location_add(ctx, location_input)
        elif args[0] == "remove" and len(args) >= 2:
            location_id = args[1]
            await self.command_handler.handle_location_remove(ctx, location_id)
        else:
            print("❌ Usage: location add <id_or_name> OR location remove <id>")

async def main():
    """Main CLI loop"""
    tester = CLITester()
    
    while True:
        try:
            command = input("\n🤖 Enter command: ")
            if not await tester.process_command(command):
                break
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            break

if __name__ == "__main__":
    asyncio.run(main())