# DisPinMap Developer Handbook

Welcome to the DisPinMap project. This document is the central source of truth for developers and contributors. It covers project architecture, development setup, testing, deployment, and contribution guidelines.

## Project Structure

- `README.md` — Project overview and user-facing info.
- `USER_DOCUMENTATION.md` — End-user guide for bot commands.
- `docs/DEVELOPER_HANDBOOK.md` — Main developer guide: setup, architecture, testing, deployment.
- `CLAUDE.md` — **AI Agent Instructions**.
  This file contains critical, project-specific instructions for Claude or other code agents.
  If you are using an AI agent to automate coding, testing, or infrastructure tasks, you (and the agent) must read this file first.

## 1. Project Architecture

The DisPinMap bot is a Python application designed to run on Google Cloud Platform (GCP).

### Core Components
- **Discord Bot**: The main application logic, built with `discord.py`. It handles user commands, schedules checks, and posts updates.
- **Database**: The bot uses SQLite for all data persistence. This is cost-effective and sufficient for all use cases. The database file is backed up to Google Cloud Storage.
- **API Clients**: The bot interacts with two external APIs:
    - [Pinball Map API](https://pinballmap.com/api/v1/docs): To fetch location and machine data.
    - [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api): To convert city names into coordinates.

### GCP Infrastructure
The application is deployed on GCP using Infrastructure as Code (IaC) with Terraform.
- **Cloud Run**: Hosts the containerized Python application. It is configured with a `min_instance_count` of 1 to maintain the persistent WebSocket connection required by Discord. Scale-to-zero is not compatible with this architecture.
- **Artifact Registry**: Stores the Docker container images.
- **Secret Manager**: Securely stores the Discord bot token.
- **Cloud Storage**: Used for backing up the SQLite database file.

## 2. Local Development Setup

1.  **Prerequisites**:
    *   Python 3.11+
    *   Docker
    *   An active Python virtual environment (`venv`).

2.  **Clone and Install**:
    ```bash
    git clone <repository-url>
    cd DisPinMap
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Environment Setup**:
    *   Copy `.env.example` to `.env`.
    *   Add your Discord bot token: `DISCORD_BOT_TOKEN="your_token_here"`

4.  **Running the Bot Locally**:
    ```bash
    python src/main.py
    ```

## 3. Testing

The project uses a sophisticated simulation framework for testing.

### Running Tests
To run the full test suite:
```bash
# Ensure you are in the project root with the venv activated
pytest
```

### Test Philosophy
- **Simulation**: Tests run in a simulated environment that mimics Discord's API and the bot's command structure. This allows for rapid, offline testing without connecting to live services.
- **Standards**: All new code requires corresponding tests. The project aims for a high level of test coverage.
- **CI Enforcement**: Linters and tests are run automatically via GitHub Actions on every pull request.

## 4. Infrastructure & Deployment

Deployment is managed via Terraform and Docker.

1.  **Prerequisites**:
    *   `gcloud` CLI, authenticated to the target GCP project.
    *   `terraform` CLI.

2.  **Infrastructure Deployment**:
    ```bash
    cd terraform
    terraform init
    terraform apply -var="gcp_project_id=YOUR_PROJECT_ID"
    ```

3.  **Application Deployment**:
    ```bash
    # Get the Artifact Registry URL from terraform output
    REPO_URL=$(terraform output -raw artifact_registry_repository_url)

    # Build and push the container
    docker build -t $REPO_URL/dispinmap-bot:latest .
    docker push $REPO_URL/dispinmap-bot:latest
    ```
    The Cloud Run service will automatically deploy the new container version.

4.  **Secret Management**:
    The Discord bot token **must** be placed in the GCP Secret Manager secret named `dispinmap-bot-discord-token`. This is a one-time manual step for security.

## 5. Contribution Workflow

Follow this workflow for all contributions.

1.  **Create a Branch**: Never commit to `main`. Always create a feature or fix branch.
    ```bash
    # Start from an up-to-date main branch
    git checkout main
    git pull
    git checkout -b feature/my-new-feature
    ```

2.  **Develop and Commit**: Make your changes. Write clear, descriptive commit messages.

3.  **Run Quality Checks**: Before submitting, run all local checks.
    ```bash
    # Run linters, formatters, and type checkers (pre-commit hooks are recommended)
    black .
    isort .
    flake8
    mypy .

    # Run tests
    pytest
    ```

4.  **Create a Pull Request**: Push your branch to GitHub and open a Pull Request against `main`. The PR must pass all automated checks before it can be merged.

## 6. AI Agent Usage

If you are using an AI code agent (such as Claude or Copilot), you must read and follow the instructions in `CLAUDE.md` in the project root. This file contains critical, project-specific instructions for agent workflows, git operations, and documentation requirements. Human contributors should also review it to understand agent conventions and expectations.

## 7. Advanced Testing: Simulation Framework

The project includes a comprehensive simulation testing framework for end-to-end validation of the Discord bot pipeline. This system allows developers to test user journeys, API interactions, and periodic monitoring without live Discord servers or APIs.

- **Key Components:**
  - Simulation orchestrator for setup/teardown and dependency injection
  - API mock system (PinballMap, Geocoding)
  - Discord simulation (mock bot, channels, users)
  - Time manipulation utilities
  - Uses real captured API responses for realism
- **Location:** See `docs/simulation-testing-framework.md` for full details and advanced usage.

## 8. Coding Standards and Development Guidelines

- Use type hints and run mypy for type checking
- Write unit tests for new features; maintain >95% test coverage
- Document all public functions/classes
- Centralize user-facing strings in `src/messages.py`
- Use proper exception handling and log errors with context
- All SQLAlchemy `DateTime` columns must be timezone-aware
- Always use a Python virtual environment
- Never commit `.env` files; keep `.env.example` up to date

## 9. Infrastructure and Deployment Best Practices

- Always use consistent resource naming: `dispinmap-bot-<component>`
- Avoid versioned naming (e.g., `-v2`) unless necessary
- Import existing GCP resources into Terraform state when needed
- Build and push container images before deploying to Cloud Run
- Discord token must be configured in Secret Manager
- Use targeted applies and verify resource readiness
- See troubleshooting and log access tips below for advanced debugging

### Log Access and Debugging Tips
- Use `gcloud run services logs read dispinmap-bot` for quick log checks
- Use Cloud Logging queries for error patterns and real-time tailing
- See `deployment-guide.md` for advanced log queries and troubleshooting

### Common Infrastructure Issues
- Resource naming conflicts: audit and clean up as needed
- Container startup failures: check Discord token, image, DB readiness, env vars
- Use Terraform import for existing resources

## 10. Product Decisions and Notification Logic

- Default notification type is `machines` (additions/removals)
- Notification types: `machines`, `comments`, `all`
- All successful checks update `last_poll_at` timestamp; failed checks do not
- See `product-specifications.md` for detailed rationale and timestamp rules

## 11. Future Improvements

- Performance optimization (DB queries, caching, background tasks)
- Enhanced error handling (retries, graceful degradation)
- Monitoring & observability (metrics, dashboards)
- Security enhancements (rate limiting, input validation, audit logging)

---

## References
- [Simulation Testing Framework](docs/simulation-testing-framework.md)
- [Product Specifications](docs/product-specifications.md) (for rationale/history)
- [Deployment Guide](docs/deployment-guide.md) (for advanced troubleshooting)
