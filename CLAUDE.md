# Project Instructions

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

## Current Status

### Test Coverage
- **126 tests PASSING** out of 129 total (97.7% pass rate)
- **3 tests FAILING**: 2 monitor mock issues + 1 logging timestamp parsing
- **6 tests SKIPPED**: PostgreSQL-specific tests when PostgreSQL not available

### Infrastructure Status
- **GCP Deployment**: ✅ **FULLY OPERATIONAL**
- **Service URL**: https://dispinmap-bot-wos45oz7vq-uc.a.run.app
- **Status**: Bot successfully deployed and running on Google Cloud Run

## Environment Assumptions for Automation

- **Assume GCP, Docker, and Terraform are already installed and authenticated.**
    - All commands can assume the correct GCP project is set, Docker is authenticated for Artifact Registry, and Terraform is initialized and has access to state.
    - No need to repeat authentication or setup steps unless explicitly requested.
- **Assume required environment variables and secrets are already configured.**
    - The bot's Discord token and database credentials are present in Secret Manager and referenced by Terraform.
- **Assume the working directory is the project root unless otherwise specified.**

*Update this section if your environment setup changes or if additional assumptions should be made for automation or agent work.*

## Lessons Learned: Complex Framework Development

### Simulation Testing Framework Implementation (June 2025)

**Key Discovery**: Building comprehensive testing frameworks for async Discord bots requires significant debugging and iteration, even with well-architected code.

**Technical Challenges Encountered:**
1. **Python 3.13 Compatibility**: `datetime.datetime.now()` became immutable, breaking traditional mock patching approaches
2. **Async Command Handling**: Discord.py commands are coroutines that require proper awaiting in simulation environments
3. **Import Path Complexity**: Module imports in testing frameworks require careful path management across different execution contexts
4. **Bot Cog Discovery**: Discord bots use dynamic command registration that doesn't work the same way in mocked environments

**Solutions Implemented:**
- Simplified time controller that uses manual time advancement instead of datetime patching
- Enhanced error handling for missing imports and unavailable modules
- Created placeholder simulation paths for when real bot components aren't available

**Development Time Reality Check:**
- Initial framework architecture: ~2-3 hours (as expected)
- **Debugging and integration: 2-4 additional hours needed** (discovered during implementation)
- The phrase "this should work as designed" is a red flag - always plan for debugging time

**Best Practices for Future Complex Frameworks:**
1. **Start with minimal viable testing** before building comprehensive simulation
2. **Test individual components in isolation** before integration
3. **Expect Python version compatibility issues** with mocking libraries
4. **Discord.py applications have unique async patterns** that require specialized handling
5. **Build incrementally with frequent testing** rather than implementing everything upfront

**Recommendation**: When estimating complex testing framework development, multiply initial time estimates by 2-3x to account for integration debugging and edge case handling.

### Development Workflow Best Practice

**Always run linting and formatting before testing:**
1. **Run lints first**: `npm run lint` or equivalent to catch syntax and style issues
2. **Fix formatting**: `black`, `isort`, `flake8` for Python projects
3. **Address all issues** before running any tests
4. **Then run tests**: Only after code is clean and formatted

This prevents test failures from masking real functionality issues and ensures consistent code quality.

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

## GCP Cost Optimization & Database Architecture

### Dual-Mode Database Design

The bot supports both SQLite and PostgreSQL modes for flexible deployment:

**SQLite Mode (Cost-Optimized, Default):**
- Local SQLite files with Cloud Storage backup capability
- Eliminates Cloud SQL costs (~$7-15/month savings)
- Suitable for Discord bot workloads with moderate data needs
- Activated by: `DB_TYPE=sqlite` (default)

**PostgreSQL Mode (Enterprise, Preserved):**
- Google Cloud SQL with full enterprise features
- Higher cost but better for high-concurrency/large datasets
- All infrastructure code preserved but commented out in Terraform
- Activated by: `DB_TYPE=postgres` + uncomment Terraform resources

### Scale-to-Zero Considerations

**Discord Bot Scale-to-Zero Compatibility:**
- ✅ **HTTP Health Checks**: Cloud Run can wake bot via `/health` endpoint
- ✅ **Command Handling**: Stateless request-response works with cold starts
- ✅ **Database Persistence**: SQLite files survive container restarts
- ⚠️ **WebSocket Reconnection**: 1-3 second delay on first command after idle
- ⚠️ **Background Tasks**: Periodic monitoring paused during scale-to-zero

**Recommended Configuration:**
```terraform
scaling {
  min_instance_count = 0  # Scale to zero when idle
  max_instance_count = 1  # Single instance sufficient
}

resources {
  limits = {
    memory = "256Mi"  # Reduced from 512Mi
    cpu    = "500m"   # Reduced from 1000m
  }
}
```

**Expected Cost Reduction:** 70-85% savings (from ~$12-15/month to ~$1.50-4/month)
