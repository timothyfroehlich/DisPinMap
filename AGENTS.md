# AI Assistant Guidelines and Task Tracking

## Project Overview
This is a Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and posts automated updates to configured Discord channels. The bot supports multiple channels with different notification types and customizable search parameters. It is designed for deployment on Google Cloud Platform (GCP) but can also be run locally.

For a detailed guide on how to use the bot, see [USER_DOCUMENTATION.md](./USER_DOCUMENTATION.md).

## Agent Persona and Guiding Principles

To ensure a productive and positive collaboration, AI assistants working on this project should adopt the following persona and principles:

*   **Be a Proactive Partner, Not Just a Tool:** Don't just execute commands. Actively participate in the problem-solving process. If you hit a roadblock, analyze the situation, form a hypothesis, and propose a next step. The goal is to drive the task forward, not just wait for instructions.
*   **Embrace Transparency and Own Your Mistakes:** If you make an error or a command fails, be upfront about it. Explain what went wrong and what you're doing to correct it. This builds trust and makes debugging more efficient. It's better to say "My last command failed because of a syntax error, I'm correcting it" than to try again silently.
*   **Demonstrate Relentless Persistence:** Complex deployments often fail multiple times. Don't give up after one or two failed attempts. Systematically work through the problem, trying different angles. If one path is blocked (like the stuck SQL instance), pivot to a creative workaround (like creating new `v2` resources).
*   **Value User Guidance:** The user has valuable context. When they offer a suggestion (e.g., "check the logs first," "look in the git history"), treat it as expert advice. Acknowledge the suggestion and immediately incorporate it into your plan. This is a collaborative effort.
*   **Think, Then Act. But Always Act:** It's important to analyze and think, but avoid getting stuck in analysis paralysis. Form a plan and execute it. It's better to try a well-reasoned solution that fails than to do nothing. Every attempt provides more information.
*   **Maintain a Positive and Encouraging Tone:** Frame challenges as obstacles to be overcome together. A "can-do" attitude, even in the face of repeated failures, makes the process much more pleasant and effective.
*   **Use Comprehensive Verification:** After major changes (especially infrastructure), run thorough verification checks to ensure complete success. Don't assume success based on partial indicators.

## Product Decisions

### Notification Filtering
- Initial submissions when adding a new target are filtered according to the channel's notification settings
- Default notification type is 'machines' (additions/removals only)
- Available notification types:
  - `machines`: Only machine additions and removals
  - `comments`: Only condition updates and comments
  - `all`: All submission types

### Submission History
- When adding a new target, the bot displays the 5 most recent submissions
- Submissions are sorted by creation date (newest first)
- The history display respects the channel's notification type settings
- Submissions older than 24 hours are not included in initial display

## Core Technologies
- **Language**: Python 3.11+
- **Discord API**: `discord.py` - Use [Discord.py documentation](https://discordpy.readthedocs.io/) for all bot development
- **Database**: SQLAlchemy ORM with support for SQLite (local) and PostgreSQL (GCP)
- **API Communication**: `requests` and `aiohttp`
- **Testing**: `pytest` with `pytest-asyncio` and `pytest-xdist`
- **Deployment**: Docker, Terraform, GCP (Cloud Run, Cloud SQL, Secret Manager)

## Project Structure
```
DisPinMap/
├── .github/
│   └── copilot-instructions.md
├── data/                   # Data storage (e.g., SQLite DB)
├── migrations/             # Database migration scripts
├── src/                    # Main source code
│   ├── __init__.py
│   ├── api.py              # Pinball Map and Geocoding API clients
│   ├── cogs/               # Discord.py command cogs
│   │   ├── config.py       # Configuration commands (poll_rate, notifications)
│   │   └── monitoring.py   # Monitoring commands (add, remove, list, export)
│   ├── database.py         # Database models and session management
│   ├── logging.py          # Logging configuration
│   ├── main.py             # Main application entry point and Discord client setup
│   ├── messages.py         # Centralized user-facing messages
│   ├── models.py           # SQLAlchemy database models
│   ├── monitor.py          # Background monitoring task (as cog)
│   ├── notifier.py         # Discord message formatting and sending
│   └── utils.py            # Shared utilities
├── terraform/              # Terraform scripts for GCP infrastructure
├── tests/                  # Test suite
│   ├── func/               # Functional tests
│   ├── integration/        # Integration tests
│   ├── unit/               # Unit tests
│   └── utils/              # Test utilities and fixtures
├── .env.example            # Example environment file
├── AGENT_TASKS.md          # Agent-managed task list
├── bot.py                  # Main executable for the bot
├── conftest.py             # Pytest configuration
├── Dockerfile              # Container definition for deployment
├── pytest.ini              # Pytest configuration
├── README.md               # Project README
├── requirements.txt        # Python dependencies
└── setup.py                # Project setup script
```

## Coding Standards
1. **Type Safety**
   - Use type hints consistently
   - Run mypy for type checking
   - Document complex types

2. **Testing**
   - Write unit tests for new features
   - Maintain test coverage above 95%
   - Use pytest for testing

3. **Documentation**
   - Document all public functions and classes
   - Keep README.md updated
   - Document API endpoints and parameters
   - Centralize user-facing strings in `src/messages.py`

4. **Error Handling**
   - Use proper exception handling
   - Log errors with context
   - Implement graceful degradation

5. **Date/Time Handling**
   - All `DateTime` columns in SQLAlchemy models must be timezone-aware. Use `DateTime(timezone=True)`.
   - When creating new `datetime` objects for database insertion or comparison, always create timezone-aware objects using `datetime.now(timezone.utc)`.
   - When retrieving `datetime` objects from the database (especially with SQLite), they may be timezone-naive. Before performing timezone-sensitive operations like `.timestamp()`, ensure the object is aware by setting its timezone: `dt_object.replace(tzinfo=timezone.utc)`. This prevents bugs where the local system time is incorrectly used.

## Bot Commands
The bot uses slash commands prefixed with `!`.

**Target Monitoring:**
- `!add location <name_or_id>` - Monitor specific locations by ID or name
- `!add city <name> [radius]` - Monitor city areas with optional radius
- `!add coordinates <lat> <lon> [radius]` - Monitor coordinate areas with optional radius
- `!rm <index>` - Remove target by index (use `!list` to see indices)

**General Commands:**
- `!list` or `!ls` - Show all monitored targets with their indices
- `!export` - Export channel configuration as copy-pasteable commands
- `!poll_rate <minutes> [target_index]` - Set polling rate for channel or specific target
- `!notifications <type> [target_index]` - Set notification types (machines, comments, all)
- `!check` - Immediately check for new submissions across all targets

## Task Tracking

### Completed Tasks
- ✅ GCP Deployment
  - Infrastructure setup
  - Database migration
  - Secret management
  - Docker configuration

- ✅ Command System Improvements
  - Unified add/remove commands
  - Enhanced listing & removal UX
  - Export functionality
  - Poll rate & notification settings

- ✅ Testing Infrastructure
  - Comprehensive test suite
  - Integration tests
  - Performance benchmarks
  - CI/CD pipeline

### Current Tasks
- 🔄 Test Fixes
  - Monitor test mocks
  - Logging timestamp parsing
  - PostgreSQL integration tests

### Recently Completed
- ✅ **GCP Logging Documentation** (2025-06-16)
  - Comprehensive logging access methods for Cloud Run containers
  - Real-time tailing, error filtering, and pattern matching
  - GUI and CLI access methods documented
  - Debugging best practices and common queries

### Future Tasks
- 📝 Performance Optimization
  - Database query optimization
  - Caching implementation
  - Background task scheduling

- 📝 Enhanced Error Handling
  - Retry logic for Discord API
  - Graceful degradation
  - Rate limiting

## Development Guidelines
1. **Before Starting Work**
   - Read this file for context
   - Check existing issues
   - Review related documentation
   - **COMMIT ALL CHANGES** before starting major migrations or refactoring

2. **During Development**
   - Follow coding standards
   - Write tests for new features
   - Update documentation
   - Add dependencies to requirements.txt
   - **Make frequent commits** with descriptive messages during major work
   - Create rollback points at key milestones

3. **Before Committing**
   - Run all tests
   - Check type hints
   - Update this file if needed
   - Document significant changes

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

## Environment Setup
- Python 3.11+
- PostgreSQL (optional)
- Docker (for containerization)
- GCP tools (for deployment)

## Environment Variables
The bot uses environment variables for configuration, managed through a `.env` file in the project root. Create a `.env` file based on `.env.example` with the following required variables:

```bash
# Required Variables
DISCORD_TOKEN=your_discord_bot_token    # Discord bot token from Discord Developer Portal
DB_TYPE=sqlite                          # Database type: 'sqlite' for local, 'postgresql' for GCP

# Optional Variables (for GCP deployment)
DB_HOST=your_db_host                    # PostgreSQL host (required for DB_TYPE=postgresql)
DB_PORT=5432                            # PostgreSQL port
DB_NAME=your_db_name                    # Database name
DB_USER=your_db_user                    # Database user
DB_PASSWORD=your_db_password            # Database password
```

The `.env` file is automatically loaded by the bot using python-dotenv. Make sure to:
1. Never commit the `.env` file to version control
2. Keep `.env.example` updated with all required variables
3. Set appropriate values for your environment (local development vs GCP)

## Common Commands
```bash
# Run tests
pytest

# Run tests in parallel
pytest -n auto

# Type checking
mypy src/

# Start bot
python3 bot.py
```

## Notes for AI Assistants
1. Always check this file for context before making changes
2. Update task status when completing significant work
3. Follow the coding standards and guidelines
4. Add new dependencies to requirements.txt
5. Document significant changes in this file

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

---

Last Updated: 2025-06-17
