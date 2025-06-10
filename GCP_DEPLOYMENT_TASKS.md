# GCP Deployment Tasks

This document contains all tasks needed to containerize and deploy the Discord bot to Google Cloud Platform.

## Phase 1: Python Application Modifications

### ✅ Task 1: Update requirements.txt with GCP dependencies
**Status**: Completed
**Details**: Added google-cloud-secret-manager, google-cloud-sql-connector[pg8000], and aiohttp

### 🔄 Task 2: Modify src/database.py for dual database support
**Status**: In Progress
**Requirements**:
- Add environment variable `DB_TYPE` to control database selection
- If `DB_TYPE=postgres`: Use google-cloud-sql-connector with these env vars:
  - `DB_INSTANCE_CONNECTION_NAME`
  - `DB_USER` 
  - `DB_PASS`
  - `DB_NAME`
- If `DB_TYPE=sqlite` or not set: Use existing SQLite logic
- Import `google.cloud.sql.connector.Connector` (try/except for local dev)
- Update `__init__` method to handle both database types
- Ensure PostgreSQL and SQLite schemas work identically

### ⏳ Task 3: Add secrets management and health check endpoint to src/main.py
**Requirements**:
**Discord Token Handling**:
- Check for `DISCORD_TOKEN_SECRET_NAME` environment variable
- If exists: Use google-cloud-secret-manager to fetch token
- If not exists: Fall back to .env file with `DISCORD_BOT_TOKEN`
- Exit if token not found in either location

**HTTP Health Check Endpoint**:
- Import asyncio and aiohttp
- Create `handle_health_check()` async function returning "OK"
- Create `start_http_server_task()` using aiohttp web app
- Listen on host/port from `PORT` environment variable
- Refactor main execution to use asyncio event loop
- Change from blocking `client.run()` to non-blocking `await client.start()`
- Run both bot and HTTP server concurrently

## Phase 2: Containerization

### ⏳ Task 4: Create Dockerfile with multi-stage build
**Requirements**:
**Stage 1 (Builder)**:
- Base: `python:3.11-slim-bullseye`
- Create virtual environment in `/opt/venv`
- Copy only `requirements.txt`
- Install dependencies with pip

**Stage 2 (Final)**:
- Same base image
- Create non-root user `appuser`
- Copy virtual environment from builder
- Copy application source (`src/`, `bot.py`)
- Set PATH to include venv bin directory
- Switch to `appuser`
- CMD: `python bot.py`

## Phase 3: Infrastructure as Code

### ⏳ Task 5: Create terraform/ directory with infrastructure files

#### terraform/versions.tf
- Require hashicorp/google provider
- Require hashicorp/random provider
- Specify Terraform version requirements

#### terraform/variables.tf
**Required variables**:
- `gcp_project_id`: GCP project ID
- `gcp_region`: GCP region (e.g., us-central1)
- `service_name`: Base name for resources (e.g., dispinmap-bot)

#### terraform/main.tf
**Resources to create**:
1. **Enabled APIs**: Cloud Run, Cloud SQL, Secret Manager, Artifact Registry
2. **Artifact Registry**: Docker repository for container images
3. **Networking**: VPC Network + VPC Access Connector for private Cloud SQL access
4. **Cloud SQL**: PostgreSQL instance + database + user with random password
5. **Secret Manager**: Secret container for Discord token (empty, manual population required)
6. **Service Account & IAM**: 
   - Service account for Cloud Run
   - "Cloud SQL Client" role
   - "Secret Manager Secret Accessor" role
7. **Cloud Run Service**:
   - `min_instance_count = 1` for continuous operation
   - Attach service account
   - Point to Artifact Registry image
   - Environment variables: `DB_TYPE=postgres`, `DB_INSTANCE_CONNECTION_NAME`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DISCORD_TOKEN_SECRET_NAME`
   - Connect to VPC connector

#### terraform/outputs.tf
**Required outputs**:
- `cloud_run_service_url`: Public URL of Cloud Run service
- `discord_token_secret_id`: Secret Manager secret ID for manual token addition
- `artifact_registry_repository_url`: Container repository URL for image pushes

## Phase 4: Configuration and Documentation

### ⏳ Task 6: Update .gitignore for Terraform files
**Add these lines**:
```
# Terraform state files
terraform.tfstate
terraform.tfstate.backup
terraform/.terraform/
*.tfvars
```

### ⏳ Task 7: Create/update .env.example with new variables
**Local development variables only**:
- `DISCORD_BOT_TOKEN=your_discord_bot_token_here`
- `DB_TYPE=sqlite` (optional, defaults to sqlite)

### ⏳ Task 8: Update README.md with deployment instructions
**Add sections for**:
**Local Development**:
- How to set up .env file with DISCORD_BOT_TOKEN

**GCP Deployment**:
- Prerequisites: gcloud CLI, terraform, docker
- Authentication commands
- Container build and push commands
- Terraform commands: init, plan, apply
- **IMPORTANT NOTE**: Manual step to add Discord token to Secret Manager after terraform apply

### ⏳ Task 9: Test local functionality still works
**Verification steps**:
- Install new requirements: `pip install -r requirements.txt`
- Run existing tests: `pytest -v`
- Start bot locally to ensure no regressions
- Verify SQLite database still works
- Test all commands function properly

## Environment Variables Summary

### Local Development (.env file)
- `DISCORD_BOT_TOKEN`: Discord bot token
- `DB_TYPE`: "sqlite" (optional, defaults to sqlite if not set)

### GCP Cloud Run (set by Terraform)
- `DB_TYPE`: "postgres"
- `DB_INSTANCE_CONNECTION_NAME`: Cloud SQL connection string
- `DB_USER`: Database username
- `DB_PASS`: Database password  
- `DB_NAME`: Database name
- `DISCORD_TOKEN_SECRET_NAME`: Secret Manager secret name
- `PORT`: HTTP server port (set by Cloud Run)

## Deployment Flow
1. Complete all code changes
2. Test locally 
3. Build and push container to Artifact Registry
4. Run terraform apply
5. Manually add Discord token to Secret Manager
6. Verify Cloud Run service is healthy