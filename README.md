# Discord Pinball Map Bot

A Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and automatically posts updates to configured Discord channels.

## Features
- **Multiple Target Monitoring**: Monitor regions, coordinates, and individual venues simultaneously
- **Global Region Support**: Access to 98 pinball regions worldwide with smart search
- **Individual Venue Tracking**: Monitor specific pinball locations like "Bender Bar" across all regions
- **Coordinate-Based Areas**: Custom lat/lon monitoring with configurable radius
- **Multi-Channel Support**: Each Discord channel can monitor different combinations independently
- **Real-Time Updates**: Instant notifications when machines are added or removed
- **Flexible Configuration**: Mix and match any combination of monitoring targets

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

**Multiple Target Monitoring:**
- `!region add <name>` / `!region remove <name>` - Monitor entire pinball regions
- `!latlong add <lat> <lon> <radius>` / `!latlong remove <lat> <lon>` - Monitor coordinate areas
- `!location add <name>` / `!location remove <name>` - Monitor specific pinball venues

**General Commands:**
- `!regions` - List all available pinball regions
- `!interval <minutes>` - Set polling interval (minimum 15 minutes)
- `!notifications <type>` - Set notification types (machines, comments, all)
- `!status` - Show current configuration and all monitored targets
- `!start` - Start monitoring all configured targets
- `!stop` - Stop monitoring for this channel
- `!check` - Immediately check for changes across all targets
- `!test` - Run 30-second simulation for testing

### Example Setup
```
!region add austin                       # Monitor Austin region
!region add montreal                     # Add Montreal region
!latlong add 40.7128 -74.0060 15        # Add NYC area with 15mi radius
!location add "Bender Bar"               # Add specific venue
!interval 30                             # Check every 30 minutes
!start                                   # Begin monitoring all targets
```
