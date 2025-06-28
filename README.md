# Discord Pinball Map Bot

[![codecov](https://codecov.io/gh/timothyfroehlich/DisPinMap/branch/main/graph/badge.svg)](https://codecov.io/gh/timothyfroehlich/DisPinMap)
[![Tests](https://github.com/timothyfroehlich/DisPinMap/workflows/Python%20Tests/badge.svg)](https://github.com/timothyfroehlich/DisPinMap/actions/workflows/python-tests.yml)
[![Lint](https://github.com/timothyfroehlich/DisPinMap/workflows/Lint%20and%20Format/badge.svg)](https://github.com/timothyfroehlich/DisPinMap/actions/workflows/lint.yml)

A Python Discord bot that continuously monitors the [pinballmap.com](https://pinballmap.com) API for changes in pinball machine locations and posts updates to Discord channels.

The project is deployed on Google Cloud Platform using Terraform and Docker.

## Features

- Monitor locations, cities, or geographic coordinates.
- Per-channel configuration for targets, poll rate, and notification types.
- Export and import configurations easily.
- Built to run efficiently on GCP Cloud Run.

---

## Getting Started

- **For Users**: To learn how to use the bot's commands in your Discord server, please see the **[User Guide](USER_DOCUMENTATION.md)**.

- **For Developers**: To contribute to the project, please consult the **[Developer Handbook](docs/DEVELOPER_HANDBOOK.md)** for a complete guide on architecture, setup, testing, and deployment.

- **For AI Agents**: If you are using an AI code agent (Claude, Copilot, etc.), see [`CLAUDE.md`](CLAUDE.md) in the project root for agent-specific instructions.

---

## Dependencies

- Python 3.8+
- Discord.py
- SQLite3
- Requests

## API Documentation

- [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) - Used for city name to coordinates conversion
- [Pinball Map API](https://pinballmap.com/api/v1/docs) - Used for fetching pinball machine data

## Recent Updates
🚀 **GCP Deployment Ready**: Added containerization and Google Cloud Platform deployment support with Terraform infrastructure as code.

## Deployment Options

### Local Development Setup
1. **Prerequisites**: Python 3.11+ installed
2. **Clone and Install**:
   ```bash
   git clone <repository-url>
   cd DisPinMap
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Environment Setup**:
   - Copy `.env.example` to `.env`
   - Add your Discord bot token: `DISCORD_BOT_TOKEN=your_token_here`
   - Discord Bot Setup:
     - Create bot at https://discord.com/developers/applications
     - Invite bot to your server with permissions: Send Messages, Read Message History, Use External Emojis

### Google Cloud Platform Deployment

**Prerequisites:**
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and configured
- [Terraform](https://www.terraform.io/downloads) installed
- [Docker](https://docs.docker.com/get-docker/) installed

**Deployment Steps:**

1. **Authentication**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Infrastructure Setup**:
   ```bash
   cd terraform
   terraform init
   terraform plan -var="gcp_project_id=YOUR_PROJECT_ID" -var="gcp_region=us-central1"
   terraform apply -var="gcp_project_id=YOUR_PROJECT_ID" -var="gcp_region=us-central1"
   ```

3. **Container Build and Deploy**:
   ```bash
   # Get the Artifact Registry URL from terraform output
   REPO_URL=$(terraform output -raw artifact_registry_repository_url)

   # Build and push container
   docker build -t $REPO_URL/dispinmap-bot:latest .
   docker push $REPO_URL/dispinmap-bot:latest
   ```

4. **⚠️ IMPORTANT: Manual Discord Token Setup**:
   After `terraform apply` completes successfully, you **MUST** manually add your Discord bot token to Google Secret Manager:

   - Go to [Secret Manager](https://console.cloud.google.com/security/secret-manager) in the GCP Console
   - Find the secret named `dispinmap-bot-discord-token` (or check `terraform output discord_token_secret_id`)
   - Click "Add Version" and paste your Discord bot token
   - The Cloud Run service will automatically restart and pick up the token

5. **Verify Deployment**:
   ```bash
   # Check service URL
   terraform output cloud_run_service_url

   # Test health endpoint
   curl $(terraform output -raw cloud_run_service_url)/health
   ```

## Usage

### Running the Bot
```bash
source venv/bin/activate
python bot.py
```

### Configuration Commands

**Target Monitoring:**
- `/add location <name_or_id>` - Monitor specific locations by ID or name
- `/add city <name> [radius]` - Monitor city areas with optional radius
- `/add coordinates <lat> <lon> [radius]` - Monitor coordinate areas with optional radius
- `/rm <index>` - Remove target by index (use `/list` to see indices)

**General Commands:**
- `/list` or `/ls` - Show all monitored targets with their indices
- `/export` - Export channel configuration as copy-pasteable commands
- `/poll_rate <minutes> [target_index]` - Set polling rate for channel or specific target
- `/notifications <type> [target_index]` - Set notification types (machines, comments, all)
- `/check` - Immediately check for new submissions across all targets

### Example Setup
```
/add city "Austin"        # Add Austin TX
/add location "Pinballz Arcade"      # Add a specific location by name
/poll_rate 30                        # Check every 30 minutes
/notifications all                   # Get all notifications
```

### Finding Location IDs
To monitor specific locations, you'll need to find their ID from the pinballmap.com website:
1. Visit https://pinballmap.com
2. Search for and navigate to the location you want to monitor
3. The location ID will be in the URL (e.g., `/locations/12345` means ID is 12345)

## Testing Bot Startup

To test that the bot can start up and connect to Discord without running indefinitely, you can use the `--test-startup` flag:

```bash
python3 src/main.py --test-startup
```

This will start the bot, wait until it connects to Discord, then immediately shut down and exit. This is useful for CI or for verifying that your environment and token are set up correctly.
