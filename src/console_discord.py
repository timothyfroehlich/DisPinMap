#!/usr/bin/env python3
"""
Console Discord Interface for Local Development

Provides a simple stdin/stdout interface to interact with Discord bot commands
without needing to use Discord during local development.
"""

import asyncio
import logging
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Import bot components
from src.cogs.command_handler import CommandHandler
from src.database import Database
from src.local_logging import get_logger

logger = get_logger('console_discord')


@dataclass
class FakeUser:
    """Fake Discord user for console simulation"""
    id: int = 999999999
    name: str = "LocalDev"
    display_name: str = "Local Developer"
    mention: str = "<@999999999>"


@dataclass
class FakeChannel:
    """Fake Discord channel for console simulation"""
    id: int = 888888888
    name: str = "console"
    mention: str = "#console"
    
    async def send(self, content: str = None, **kwargs) -> None:
        """Simulate sending a message to the channel"""
        if content:
            # Print bot responses with timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            logger.info(f"[{timestamp}] [BOT] {content}")


@dataclass
class FakeGuild:
    """Fake Discord guild/server for console simulation"""
    id: int = 777777777
    name: str = "Local Development Server"


@dataclass
class FakeMessage:
    """Fake Discord message for console simulation"""
    content: str
    author: FakeUser
    channel: FakeChannel
    guild: FakeGuild
    
    def __init__(self, content: str):
        self.content = content
        self.author = FakeUser()
        self.channel = FakeChannel()
        self.guild = FakeGuild()


class ConsoleInterface:
    """Console interface for Discord bot interaction"""
    
    def __init__(self, bot, database: Database):
        self.bot = bot
        self.database = database
        self.command_handler = None
        self.running = False
        self.input_thread = None
        
    async def setup(self):
        """Initialize the console interface"""
        logger.info("🖥️  Setting up console Discord interface...")
        
        # Get the command handler cog
        self.command_handler = self.bot.get_cog("CommandHandler")
        if not self.command_handler:
            logger.error("❌ CommandHandler cog not found!")
            return False
            
        logger.info("✅ Console interface ready!")
        logger.info("💡 Available commands:")
        logger.info("   !add location \"<name>\" - Add location monitoring")
        logger.info("   !list - Show monitored targets")
        logger.info("   !check - Manual check all targets")
        logger.info("   !status - Show monitoring status")
        logger.info("   .quit - Exit console")
        logger.info("   .trigger - Force monitoring loop iteration")
        logger.info("   .health - Show bot health status")
        logger.info("")
        logger.info("Type commands and press Enter:")
        
        return True
    
    def start_input_thread(self):
        """Start the input handling thread"""
        self.running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        
    def stop(self):
        """Stop the console interface"""
        self.running = False
        logger.info("🛑 Console interface stopped")
        
    def _input_loop(self):
        """Input handling loop (runs in separate thread)"""
        while self.running:
            try:
                # Read input from stdin
                user_input = input("> ").strip()
                if not user_input:
                    continue
                    
                # Schedule command processing in the event loop
                asyncio.create_task(self._process_command(user_input))
                
            except EOFError:
                # Handle Ctrl+D
                logger.info("🔚 EOF received, stopping console interface")
                self.running = False
                break
            except KeyboardInterrupt:
                # Handle Ctrl+C
                logger.info("🔚 Keyboard interrupt, stopping console interface")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ Error in input loop: {e}")
    
    async def process_command(self, user_input: str):
        """Process a command from any input source (console or file)"""
        return await self._process_command(user_input)
    
    async def _process_command(self, user_input: str):
        """Internal command processing"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{timestamp}] [USER] > {user_input}")
        
        # Handle special console commands
        if user_input == ".quit":
            logger.info("👋 Goodbye!")
            self.running = False
            return
            
        elif user_input == ".trigger":
            await self._trigger_monitoring()
            return
            
        elif user_input == ".health":
            await self._show_health_status()
            return
            
        elif user_input == ".status":
            await self._show_monitoring_status()
            return
        
        # Handle Discord bot commands
        if user_input.startswith("!"):
            await self._process_bot_command(user_input)
        else:
            logger.info("[BOT] ❓ Unknown command. Try !help or .quit")
    
    async def _process_bot_command(self, command: str):
        """Process a Discord bot command"""
        try:
            # Create fake message
            fake_message = FakeMessage(command)
            
            # Process the command through the command handler
            if command.startswith("!add"):
                await self.command_handler.add_location(fake_message, *command.split()[1:])
            elif command.startswith("!list"):
                await self.command_handler.list_targets(fake_message)
            elif command.startswith("!check"):
                await self.command_handler.manual_check(fake_message)
            elif command.startswith("!remove"):
                await self.command_handler.remove_location(fake_message, *command.split()[1:])
            elif command.startswith("!help"):
                await self.command_handler.show_help(fake_message)
            else:
                logger.info("[BOT] ❓ Unknown command. Available: !add, !list, !check, !remove, !help")
                
        except Exception as e:
            logger.error(f"❌ Error processing command '{command}': {e}")
            logger.info("[BOT] ❌ Command failed - check logs for details")
    
    async def _trigger_monitoring(self):
        """Trigger a manual monitoring loop iteration"""
        try:
            runner_cog = self.bot.get_cog("MonitoringRunner")
            if runner_cog and hasattr(runner_cog, 'monitor_task_loop'):
                logger.info("🔄 Triggering monitoring loop iteration...")
                # This will trigger the next iteration immediately
                runner_cog.monitor_task_loop.restart()
                logger.info("✅ Monitoring loop triggered")
            else:
                logger.warning("⚠️ Monitoring runner not found or not running")
        except Exception as e:
            logger.error(f"❌ Error triggering monitoring: {e}")
    
    async def _show_health_status(self):
        """Show bot health status"""
        try:
            # Check Discord connection
            discord_status = "🟢 Connected" if self.bot.is_ready() else "🔴 Disconnected"
            
            # Check database
            try:
                with self.database.get_session() as session:
                    # Simple query to test database
                    from src.models import MonitoringTarget
                    count = session.query(MonitoringTarget).count()
                    db_status = f"🟢 Connected ({count} targets)"
            except Exception as e:
                db_status = f"🔴 Error: {e}"
            
            # Check monitoring loop
            runner_cog = self.bot.get_cog("MonitoringRunner")
            if runner_cog and hasattr(runner_cog, 'monitor_task_loop'):
                if runner_cog.monitor_task_loop.is_running():
                    loop_status = f"🟢 Running (iteration #{runner_cog.monitor_task_loop.current_loop})"
                else:
                    loop_status = "🔴 Stopped"
            else:
                loop_status = "🔴 Not found"
            
            logger.info("🏥 Bot Health Status:")
            logger.info(f"   Discord: {discord_status}")
            logger.info(f"   Database: {db_status}")
            logger.info(f"   Monitoring Loop: {loop_status}")
            
        except Exception as e:
            logger.error(f"❌ Error checking health: {e}")
    
    async def _show_monitoring_status(self):
        """Show current monitoring status"""
        try:
            with self.database.get_session() as session:
                from src.models import MonitoringTarget, ChannelConfig
                
                # Get target counts
                total_targets = session.query(MonitoringTarget).count()
                active_channels = session.query(ChannelConfig).count()
                
                logger.info("📊 Monitoring Status:")
                logger.info(f"   Total targets: {total_targets}")
                logger.info(f"   Active channels: {active_channels}")
                
                # Show recent targets
                recent_targets = session.query(MonitoringTarget).limit(5).all()
                if recent_targets:
                    logger.info("   Recent targets:")
                    for target in recent_targets:
                        logger.info(f"     - {target.location_name} (ID: {target.location_id})")
                
        except Exception as e:
            logger.error(f"❌ Error getting monitoring status: {e}")


# Convenience function for local development entry point
async def create_console_interface(bot, database: Database) -> ConsoleInterface:
    """Create and setup console interface"""
    interface = ConsoleInterface(bot, database)
    success = await interface.setup()
    if success:
        interface.start_input_thread()
        return interface
    else:
        raise RuntimeError("Failed to setup console interface")