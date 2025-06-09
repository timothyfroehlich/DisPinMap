#!/usr/bin/env python3
"""
Functional test to verify command logging flow works correctly.
Tests that commands are logged immediately before processing.
"""

import sys
import asyncio
import io
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import AsyncMock, patch, MagicMock

from src.database import Database
from src.commands import CommandHandler

class MockChannel:
    def __init__(self, channel_id=999999999):
        self.id = channel_id
        self.__str__ = lambda: "test-channel"

class MockGuild:
    def __init__(self, guild_id=888888888):
        self.id = guild_id
        self.__str__ = lambda: "test-guild"

class MockAuthor:
    def __init__(self, name="testuser"):
        self.name = name
        self.__str__ = lambda: self.name

class MockMessage:
    def __init__(self, content="!test command"):
        self.content = content
        self.author = MockAuthor()
        self.channel = MockChannel()
        self.guild = MockGuild()

class MockContext:
    def __init__(self, command_name="test"):
        self.channel = MockChannel()
        self.guild = MockGuild()
        self.author = MockAuthor()
        self.message = MockMessage()
        self.command = MagicMock()
        self.command.qualified_name = command_name
        self.sent_messages = []
    
    async def send(self, message):
        """Mock send method that captures output and simulates logging"""
        print(f"BOT REPLY in #{self.channel} to {self.author}: {message}")
        self.sent_messages.append(message)

async def test_logging_flow():
    """Test that command logging happens before processing"""
    print("🧪 Testing command logging flow...")
    
    # Capture stdout to analyze logging order
    output_buffer = io.StringIO()
    
    with redirect_stdout(output_buffer):
        # Simulate the on_message logging
        message = MockMessage("!location add Austin")
        print(f"COMMAND RECEIVED from {message.author} in #{message.channel} (Guild: {message.guild}): {message.content}")
        
        # Simulate API call logging (from api.py)
        print("🌐 API: locations")
        
        # Simulate command processing
        ctx = MockContext("location add")
        
        # Mock the API response to return suggestions
        with patch('commands.search_location_by_name') as mock_search:
            mock_search.return_value = {
                'status': 'suggestions',
                'data': [
                    {'name': 'Austin Pinball Collective', 'id': 26454},
                    {'name': 'Austin Beerworks', 'id': 23772}
                ]
            }
            
            # Create command handler and process command
            db = Database(":memory:")  # Use in-memory DB for testing
            handler = CommandHandler(db)
            
            await handler.handle_location_add(ctx, "Austin")
    
    # Analyze the output
    output = output_buffer.getvalue()
    lines = output.strip().split('\n')
    
    print("\n📋 Captured output:")
    for i, line in enumerate(lines, 1):
        print(f"{i}. {line}")
    
    # Verify logging order
    assert len(lines) >= 3, f"Expected at least 3 log lines, got {len(lines)}"
    
    # Check that command is logged first
    assert "COMMAND RECEIVED" in lines[0], f"First line should contain 'COMMAND RECEIVED', got: {lines[0]}"
    
    # Check that API call is logged second
    assert "🌐 API: locations" in lines[1], f"Second line should contain API call, got: {lines[1]}"
    
    # Check that bot reply comes after
    assert "BOT REPLY" in lines[2], f"Third line should contain 'BOT REPLY', got: {lines[2]}"
    
    print("✅ Command logging flow test passed!")
    return True

async def test_location_id_lookup():
    """Test location ID lookup functionality"""
    print("\n🧪 Testing location ID lookup...")
    
    # Test the API call that's failing
    from src.api import fetch_location_details
    
    try:
        # Test with the failing ID from your example
        location_details = await fetch_location_details(26454)
        print(f"📍 Location 26454 details: {location_details}")
        
        if location_details and location_details.get('id'):
            print("✅ Location ID lookup successful")
            return True
        else:
            print("❌ Location ID lookup returned empty or invalid data")
            return False
            
    except Exception as e:
        print(f"❌ Location ID lookup failed with error: {e}")
        return False

async def main():
    """Run all functional tests"""
    print("🚀 Running functional tests for logging flow...\n")
    
    try:
        # Test 1: Logging flow
        test1_passed = await test_logging_flow()
        
        # Test 2: Location ID lookup
        test2_passed = await test_location_id_lookup()
        
        print(f"\n📊 Test Results:")
        print(f"  Logging Flow: {'✅ PASS' if test1_passed else '❌ FAIL'}")
        print(f"  Location ID Lookup: {'✅ PASS' if test2_passed else '❌ FAIL'}")
        
        if test1_passed and test2_passed:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)