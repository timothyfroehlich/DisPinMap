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
