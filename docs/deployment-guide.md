# Deployment Guide

## GCP Deployment Configuration

### CRITICAL: Correct Project Information
- **GCP Project ID**: `andy-expl` (NOT `pinballmap-bot`)
- **Region**: `us-central1`
- **Service Name**: `dispinmap-bot`
- **Artifact Registry**: `dispinmap-bot-repo`

This information is defined in:
- `terraform/terraform.tfvars`: Contains the actual project values
- `terraform/variables.tf`: Contains variable definitions

### Deployment Process

#### 1. Pre-deployment Setup
```bash
# Set correct GCP project
gcloud config set project andy-expl

# Authenticate Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### 2. Build and Push Docker Image
```bash
# Build the image
docker build -t us-central1-docker.pkg.dev/andy-expl/dispinmap-bot-repo/dispinmap-bot:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/andy-expl/dispinmap-bot-repo/dispinmap-bot:latest
```

#### 3. Deploy to Cloud Run
```bash
# Deploy new version
gcloud run deploy dispinmap-bot \
    --image us-central1-docker.pkg.dev/andy-expl/dispinmap-bot-repo/dispinmap-bot:latest \
    --region us-central1 \
    --platform managed
```

#### 4. Verify Deployment
```bash
# Check Cloud Run service status
gcloud run services list --region=us-central1

# Check logs to ensure bot started properly
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot" \
    --limit=20 --format="table(timestamp,textPayload)" --project andy-expl
```

#### 5. Common Issues
- **Wrong Project**: Always use `andy-expl`, NOT `pinballmap-bot`
- **Authentication**: Make sure Docker is authenticated with `gcloud auth configure-docker`
- **Repository Names**: The service is `dispinmap-bot`, repository is `dispinmap-bot-repo`

### Accessing Logs for Debugging

#### Quick Log Access Methods

**1. Console-Optimized Format (Best for quick checks)**
```bash
gcloud run services logs read dispinmap-bot --limit=10 --project andy-expl --region=us-central1
```

**2. Cloud Logging with Formatted Output (Best for detailed debugging)**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot" \
    --project andy-expl --limit 10 --format="table(timestamp,severity,textPayload)"
```

**3. Real-Time Log Tailing (Best for active debugging)**
```bash
# First-time setup (if needed):
sudo apt-get install google-cloud-cli-log-streaming

# Then tail logs in real-time:
gcloud beta run services logs tail dispinmap-bot --project andy-expl --region=us-central1
```

**4. Error-Only Logs (Critical for troubleshooting)**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot AND severity=ERROR" \
    --project andy-expl --limit 10
```

**5. Search for Specific Error Patterns**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot AND textPayload:\"RuntimeError\"" \
    --project andy-expl --limit 5 --format="table(timestamp,severity,textPayload)"
```

**6. Custom Formatted Logs (Compact view)**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot" \
    --project andy-expl --limit 5 --format="value(timestamp,severity,textPayload)" --freshness=1d
```

#### Console Access (GUI)

**Cloud Run Logs**
- Navigate to: [Cloud Run Console](https://console.cloud.google.com/run?project=andy-expl)
- Click on `dispinmap-bot` service
- Go to **LOGS** tab

**Logs Explorer (Advanced)**
- Navigate to: [Logs Explorer](https://console.cloud.google.com/logs/query?project=andy-expl)
- Use resource: **Cloud Run Revision**
- Service name: `dispinmap-bot`

#### Debugging Best Practices

1. **Start with Recent Logs**: Use `--limit=10` first to see latest activity
2. **Filter by Severity**: Use `severity=ERROR` for critical issues
3. **Use Pattern Matching**: Search for specific error types with `textPayload:"ErrorType"`
4. **Time-Based Queries**: Add `--freshness=1d` to limit to recent logs
5. **Real-Time Monitoring**: Use `tail` command during active debugging (requires `google-cloud-cli-log-streaming` package)
6. **Structured Queries**: Combine multiple filters for precise debugging

#### Prerequisites for Full Functionality
- **Log Streaming**: Install with `sudo apt-get install google-cloud-cli-log-streaming` for real-time tailing
- **Project Access**: Ensure you're authenticated with `gcloud auth login` and have proper IAM permissions

#### Common Log Sources
- **Request Logs**: HTTP requests to the service (automatic)
- **Container Logs**: Application stdout/stderr (our bot logs)
- **System Logs**: Container startup/health check failures

#### Useful Log Queries
```bash
# Show startup failures
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot AND textPayload:\"STARTUP TCP probe failed\"" --project andy-expl --limit 5

# Show Discord connection issues
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot AND textPayload:\"discord\"" --project andy-expl --limit 10

# Show database connection issues
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dispinmap-bot AND textPayload:\"database\"" --project andy-expl --limit 10
```

### Infrastructure Details
- **Cloud Run Service**: `dispinmap-bot`
- **PostgreSQL Instance**: `dispinmap-bot-db-instance`
- **Database**: `dispinmap-bot`
- **Database User**: `dispinmap-bot-user`
- **Artifact Registry**: `dispinmap-bot-repo`
- **Service Account**: `dispinmap-bot-sa`
- **Secrets**:
  - `dispinmap-bot-discord-token` (configured)
  - `dispinmap-bot-db-password` (auto-generated)
- **Service URL**: https://dispinmap-bot-wos45oz7vq-uc.a.run.app
- **Status**: ✅ **FULLY OPERATIONAL** (as of 2025-06-17)

### Common Infrastructure Issues and Solutions

#### V2 Naming Problems
**Issue**: Resources created with `-v2` suffixes causing confusion and deployment conflicts.

**Solution Process**:
1. Audit all GCP resources: `gcloud run services list`, `gcloud sql instances list`, etc.
2. Systematically delete v2 resources: `gcloud <service> delete <resource-v2>`
3. Verify terraform configuration uses correct naming
4. Import existing properly-named resources into terraform state
5. Run comprehensive verification checks

#### Container Startup Failures
**Issue**: Cloud Run service fails with "container failed to start and listen on port 8080"

**Common Causes & Solutions**:
1. **Missing Discord Token**: Check secret has value with `gcloud secrets versions describe`
2. **Wrong Image**: Verify image exists with `gcloud container images list-tags`
3. **Database Not Ready**: Ensure SQL instance state is `RUNNABLE`
4. **Environment Variables**: Check terraform configuration matches expected env vars

#### Terraform Import Workflows
**When to Import**: Resource exists in GCP but not in terraform state

**Process**:
```bash
# Example: Import existing SQL instance
terraform import google_sql_database_instance.postgres_instance instance-name

# Verify import worked
terraform plan  # Should show no changes for imported resource
```

## Infrastructure Management Best Practices

### Resource Naming Conventions
- **Always use consistent naming**: All resources should follow the pattern `dispinmap-bot-<component>`
- **Avoid versioned naming**: Never use `v2`, `v3`, etc. in resource names unless absolutely necessary
- **Verify naming across all resources**: Check GCP console, terraform state, and configuration files

### Infrastructure Cleanup Process
1. **Audit existing resources**: Use `gcloud` CLI to list all resources with problematic naming
2. **Document current state**: Record what exists before making changes
3. **Plan systematic cleanup**: Remove old resources before creating new ones
4. **Verify complete cleanup**: Run comprehensive checks to ensure no remnants remain

### Container Deployment Requirements
- **Discord token must be configured**: Bot will fail to start without a valid Discord token in Secret Manager
- **Build and push images first**: Cloud Run cannot deploy non-existent container images
- **Test service health**: Always verify the deployed service responds correctly (HTTP 200)
- **Check logs for errors**: Monitor Cloud Run logs during and after deployment

### Terraform State Management
- **Import existing resources**: When resources exist outside terraform, import them rather than recreating
- **Handle timing issues**: SQL instances and other resources may take time to become ready
- **Use targeted applies**: Use `-target` for specific resource deployment when needed

## Commit Management
- **Always commit before major migrations**: Create a clean rollback point
- **Use descriptive commit messages**: Include context about what phase of work
- **Commit incrementally**: Don't batch large changes into single commits
- **Create milestone commits**: Mark completion of major components
- **Test before committing**: Ensure changes don't break existing functionality