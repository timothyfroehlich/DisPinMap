# Infrastructure Agent Instructions

## GCP Architecture
- **Cloud Run** - Containerized Discord bot (always-on with min_instance_count=1)
- **Artifact Registry** - Docker image storage and versioning
- **Secret Manager** - Discord bot token secure storage
- **Cloud Storage** - SQLite database backup storage

## Key Files
- **main.tf** - Core GCP resources and configuration
- **variables.tf** - Input parameters with validation
- **outputs.tf** - Service URLs, resource IDs for other tools
- **versions.tf** - Terraform and provider version constraints

## Critical Settings
```hcl
# Cloud Run MUST have min_instance_count = 1
# Discord WebSocket requires persistent connection
min_instance_count = 1

# Container listens on port 8080 for health checks
port = 8080
```

## Deployment Commands
```bash
# Build and push new image
docker build -t us-central1-docker.pkg.dev/andy-expl/dispinmap-bot-repo/dispinmap-bot:latest .
docker push us-central1-docker.pkg.dev/andy-expl/dispinmap-bot-repo/dispinmap-bot:latest

# Deploy to Cloud Run
terraform apply -auto-approve

# Verify deployment
curl -f https://dispinmap-bot-wos45oz7vq-uc.a.run.app/health
```

## Environment Assumptions
**IMPORTANT**: These are assumed to be already configured:
- GCP project authenticated (`gcloud auth login`)
- Docker authenticated to Artifact Registry
- Terraform state backend configured (not local)
- Service account permissions granted

## Resource Dependencies
1. **Artifact Registry** must exist before image push
2. **Secret Manager** must contain Discord token
3. **Cloud Run** service references both registry and secrets
4. **Storage bucket** for database backups

## Service Details
- **URL**: https://dispinmap-bot-wos45oz7vq-uc.a.run.app
- **Health endpoint**: `/health` returns "OK"
- **Logging**: Cloud Run logs accessible via `gcloud run services logs read`
- **Scaling**: Min 1 instance, max based on load

## Troubleshooting
```bash
# Check service status
gcloud run services describe dispinmap-bot --region=us-central1

# View recent logs
gcloud run services logs read dispinmap-bot --region=us-central1 --limit=50

# Force new deployment
terraform apply -replace=google_cloud_run_v2_service.bot_service
```

## Security Notes
- Service account follows least-privilege principle
- Discord token stored in Secret Manager, never in code
- Cloud Run service not publicly accessible except health endpoint
- All traffic over HTTPS only
