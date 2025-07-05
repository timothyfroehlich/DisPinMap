# Console Interface Limited Commands

**Priority**: 2 **Type**: bug **Status**: open **Created**: 2025-07-05
**Updated**: 2025-07-05

## Description

The local development console interface only supports a subset of Discord bot
commands due to hardcoded command mapping instead of using Discord.py's command
processing system.

## Reproduction Steps

1. Start local development: `python local_dev.py`
2. Try commands like `!poll_rate 5` or `!help`
3. Observe "Unknown command" errors
4. Only `!add`, `!list`, `!check`, `!remove` work partially

## Expected vs Actual Behavior

- **Expected**: All Discord bot commands should work in console interface
- **Actual**: Only 5 commands are hardcoded and mapped, others fail with
  "Unknown command"

## Technical Details

### Root Cause

The console interface in `src/local_dev/console_discord.py` has an architecture
mismatch:

1. **Hardcoded command mapping**: Only these commands are manually mapped:

   ```python
   if command.startswith("!add"):
       await self.command_handler.add_location(fake_message, *command.split()[1:])
   elif command.startswith("!list"):
       await self.command_handler.list_targets(fake_message)
   # etc...
   ```

2. **Bypasses Discord.py framework**: Should use `bot.process_commands()`
   instead
3. **Method name mismatches**: Calls `show_help()` but real method is
   `help_command()`

### Missing Commands

- `!poll_rate` - Set polling frequency
- `!notifications` - Configure notification types
- `!export` - Export configuration
- `!monitor_health` - Show monitoring health
- All other commands in `src/cogs/command_handler.py`

### Current Error Examples

```
[CONSOLE] ERROR - ❌ Error processing command '!help': 'CommandHandler' object has no attribute 'show_help'
[CONSOLE] INFO - [BOT] ❓ Unknown command. Available: !add, !list, !check, !remove, !help
```

## Proposed Solution

### Option 1: Use Discord.py Command Processing (Recommended)

Refactor console interface to use `bot.process_commands()`:

```python
async def _process_bot_command(self, command: str):
    """Process command through Discord.py's command system"""
    try:
        # Create proper fake message object
        fake_message = FakeMessage(command)
        fake_message.author = FakeUser()
        fake_message.channel = FakeChannel()
        fake_message.guild = FakeGuild()

        # Process through Discord.py command system
        await self.bot.process_commands(fake_message)

    except Exception as e:
        logger.error(f"❌ Error processing command '{command}': {e}")
```

### Option 2: Auto-generate Command Mapping

Dynamically discover and map all commands from loaded cogs:

```python
def _build_command_mapping(self):
    """Build command mapping from all loaded cogs"""
    self.command_mapping = {}
    for cog_name, cog in self.bot.cogs.items():
        for command in cog.get_commands():
            self.command_mapping[command.name] = command
```

## Acceptance Criteria

- [ ] All Discord bot commands work in console interface
- [ ] No hardcoded command mapping required
- [ ] Error handling consistent with Discord bot
- [ ] Special console commands (`.quit`, `.status`, etc.) still work
- [ ] Proper fake Discord context objects provided

## Impact

- **Development workflow**: Limited testing capabilities for configuration
  commands
- **Debugging**: Cannot test poll rate changes, notification settings via
  console
- **User experience**: Confusing that documented commands don't work

## Notes

- Monitoring loop itself works correctly - this is only a console interface
  issue
- Commands work fine in actual Discord environment
- Console interface was designed for basic testing, needs expansion for full
  functionality

## Related Files

- `src/local_dev/console_discord.py` - Main console interface
- `src/cogs/command_handler.py` - All Discord commands
- `docs/LOCAL_DEVELOPMENT.md` - Documentation of console commands
