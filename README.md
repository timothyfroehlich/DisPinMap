# Discord Pinball Map Bot

A Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and automatically posts updates to configured Discord channels.

## Features
- **Coordinate-Based Monitoring**: Monitor any geographic area using lat/lon coordinates with custom radius
- **Individual Location Tracking**: Monitor specific pinball locations by ID
- **Multi-Channel Support**: Each Discord channel can monitor different combinations independently
- **Real-Time Updates**: Instant notifications when machines are added or removed
- **Flexible Configuration**: Mix and match coordinate areas and specific locations

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
