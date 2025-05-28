# Discord Pinball Map Bot

A Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and automatically posts updates to configured Discord channels.

## Features
- **Automated Monitoring**: Background polling of pinballmap.com API at configurable intervals
- **Multi-Channel Support**: Each Discord channel can monitor different locations independently
- **Flexible Notifications**: Configure channels to track machine additions/removals, comments, or both
- **Customizable Search**: Set custom location center point and search radius per channel
- **Persistent Configuration**: All settings and tracking data survive bot restarts
- **Real-Time Updates**: Instant Discord notifications when changes are detected

## Setup
1. **Prerequisites**: Python 3.8+ installed
2. **Clone and Install**:
   ```bash
   git clone <repository-url>
   cd DiscordPinballMap
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Discord Bot Setup**:
   - Create bot at https://discord.com/developers/applications
   - Copy bot token to `.env` file: `DISCORD_BOT_TOKEN=your_token_here`
   - Invite bot to your server with permissions: Send Messages, Read Message History, Use External Emojis

## Usage

### Running the Bot
```bash
source venv/bin/activate
python bot.py
```

### Configuration Commands
- `!configure location <lat> <lon>` - Set search center point
- `!configure radius <miles>` - Set search radius (default: 25 miles)
- `!configure poll_rate <minutes>` - Set polling interval (default: 60 minutes, minimum: 15)
- `!configure notifications <type>` - Set notification types: `machines`, `comments`, or `all`
- `!start` - Begin monitoring for this channel
- `!stop` - Stop monitoring for this channel
- `!status` - View current channel configuration
- `!machines` - Manual list of current machines in area

### Example Setup
```
!configure location 30.2672 -97.7431    # Austin, TX coordinates
!configure radius 30                      # 30 mile radius
!configure notifications machines         # Only machine additions/removals
!start                                   # Begin monitoring
```
