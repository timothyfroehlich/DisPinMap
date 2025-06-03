# Discord Pinball Map Bot

A Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and automatically posts updates to configured Discord channels.

## Features
- **Coordinate-Based Monitoring**: Monitor any geographic area using lat/lon coordinates with custom radius
- **Individual Location Tracking**: Monitor specific pinball locations by ID
- **Multi-Channel Support**: Each Discord channel can monitor different combinations independently
- **Real-Time Updates**: Instant notifications when machines are added or removed
- **Flexible Configuration**: Mix and match coordinate areas and specific locations

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

**Target Monitoring:**
- `!latlong add <lat> <lon> <radius>` / `!latlong remove <lat> <lon>` - Monitor coordinate areas
- `!location add <location_id>` / `!location remove <location_id>` - Monitor specific locations by ID

**General Commands:**
- `!interval <minutes>` - Set polling interval (minimum 15 minutes)
- `!notifications <type>` - Set notification types (machines, comments, all)
- `!status` - Show current configuration and all monitored targets
- `!start` - Start monitoring all configured targets
- `!stop` - Stop monitoring for this channel
- `!check` - Immediately check for changes across all targets
- `!test` - Run 30-second simulation for testing

### Example Setup
```
!latlong add 40.7128 -74.0060 15        # Add NYC area with 15mi radius
!location add 12345                      # Add specific location by ID
!interval 30                             # Check every 30 minutes
!start                                   # Begin monitoring all targets
```

### Finding Location IDs
To monitor specific locations, you'll need to find their ID from the pinballmap.com website:
1. Visit https://pinballmap.com
2. Search for and navigate to the location you want to monitor
3. The location ID will be in the URL (e.g., `/locations/12345` means ID is 12345)
