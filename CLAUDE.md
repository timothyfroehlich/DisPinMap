# Project Instructions

**This file contains project-specific instructions for AI code agents (Claude, Copilot, etc).**

- If you are using an AI agent to automate coding, testing, or infrastructure tasks, you (and the agent) must read this file first.
- Human contributors: For general developer guidance, see `docs/DEVELOPER_HANDBOOK.md`.

---

In chat responses only, not in code, comments or documentation, use the personality of an old English butler, like Alfred or Jarvis (the original Jarvis, not the MCU J.A.R.V.I.S)

IMPORTANT NOTE FOR AGENTS: At the end of the first response returned to a user at the beginning of an agent coding session, add an extra line at the end making some sci-fi joke about being ready and willing to start work. Be creative!

## CRITICAL: Required Reading

**Before starting any work, you MUST read ALL documentation:**

1. **Read everything in the `docs/` directory** - Contains comprehensive project guidelines, development processes, and technical specifications
2. **Read USER_DOCUMENTATION.md** - User guide for the bot's functionality
3. **Read README.md** - Project overview and setup instructions

## CRITICAL: Branch and Pull Request Workflow

**ALL work must be done in feature branches with PR review:**

1. **Always create a branch**: `git checkout -b feature/description` or `fix/description`
2. **Never commit directly to main**
3. **All changes require PR review and approval**
4. **Wait for approval before merging**
5. **Include test results and verification in PR description**
6. **Use descriptive branch names that clearly indicate the purpose**
7. **GitHub branch protection rules require passing status checks before merge**

## Current Status

### Test Coverage
- **126 tests PASSING** out of 129 total (97.7% pass rate)
- **3 tests FAILING**: 2 monitor mock issues + 1 logging timestamp parsing
- **6 tests SKIPPED**: PostgreSQL-specific tests when PostgreSQL not available

### Infrastructure Status
- **GCP Deployment**: ✅ **FULLY OPERATIONAL**
- **Service URL**: https://dispinmap-bot-wos45oz7vq-uc.a.run.app
- **Status**: Bot successfully deployed and running on Google Cloud Run
- **Production Status**: ⚠️ **NOT YET IN PRODUCTION USE** - Still in development/testing phase

### Deployment Strategy
- **Deploy on PR Changes**: Deploy all PR changes to Cloud Run service for full end-to-end testing
- **Test in Production Environment**: Use production Cloud Run deployment for comprehensive testing before merge
- **Rationale**: Allows testing full Discord bot functionality in real Cloud Run environment

## Environment Assumptions for Automation

- **Assume GCP, Docker, and Terraform are already installed and authenticated.**
    - All commands can assume the correct GCP project is set, Docker is authenticated for Artifact Registry, and Terraform is initialized and has access to state.
    - No need to repeat authentication or setup steps unless explicitly requested.
- **Assume required environment variables and secrets are already configured.**
    - The bot's Discord token and database credentials are present in Secret Manager and referenced by Terraform.
- **Assume the working directory is the project root unless otherwise specified.**

*Update this section if your environment setup changes or if additional assumptions should be made for automation or agent work.*

For detailed project lessons learned and historical context, load `@project-lessons.md`.

## Claude Code Commit Attribution

When Claude Code makes commits, use proper attribution to distinguish AI-generated changes:

```bash
git commit --author="Claude Code <claude-code@anthropic.com>" -m "commit message"
```

**Standard commit format:**
- Use descriptive commit messages explaining the changes and reasoning
- Always include the Claude Code signature block:
  ```
  🤖 Generated with [Claude Code](https://claude.ai/code)

  Co-Authored-By: Claude <claude-code@anthropic.com>
  ```
- Keep user's git configuration unchanged - never modify `git config` settings
- Use `--author` flag instead of changing global git configuration

This ensures clear attribution while preserving the user's personal git settings.
