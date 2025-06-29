# Project Instructions

**This file contains project-specific instructions for AI code agents (Claude, Copilot, etc).**

- If you are using an AI agent to automate coding, testing, or infrastructure tasks, you (and the agent) must read this file first.
- Human contributors: For general developer guidance, see `docs/DEVELOPER_HANDBOOK.md`.

---

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
- **181 tests PASSING** out of 187 total (96.8% pass rate)
- **6 tests FAILING**: API response format mismatches and database model issues (see Issue #61)
- **0 tests SKIPPED**: PostgreSQL-specific tests when PostgreSQL not available

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

## CRITICAL: Mock Specifications Required

**ALL mocks MUST use proper `spec` parameters to enforce interface compliance:**

### Mock Requirements:
1. **ALWAYS use spec-based factories** from `tests/utils/mock_factories.py`
2. **NEVER use raw `Mock()` or `MagicMock()` without specs**
3. **Use `autospec=True`** for all `@patch` decorators
4. **Validate mock specs** to catch interface violations early

### Factory Functions (REQUIRED):
- `create_async_notifier_mock()` - For Notifier class mocks
- `create_database_mock()` - For Database class mocks
- `create_bot_mock()` - For Discord Bot mocks
- `create_discord_context_mock()` - For Discord Context mocks
- `create_requests_response_mock()` - For HTTP Response mocks

### Examples:
```python
# ❌ WRONG - No spec validation
mock_notifier = Mock()

# ✅ CORRECT - Spec-based factory with interface validation
mock_notifier = create_async_notifier_mock()

# ❌ WRONG - Basic patching
@patch("requests.get")

# ✅ CORRECT - Autospec patching
@patch("requests.get", autospec=True)
```

**Rationale**: Spec-based mocks catch interface changes at test time, preventing runtime failures and ensuring tests accurately reflect production behavior.

## Other

Never use src.path.append for imports.
