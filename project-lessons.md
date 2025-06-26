# Project Lessons Learned

Load this file with `@project-lessons.md` when you need detailed historical context about project development challenges and solutions.

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

### Scale-to-Zero Analysis Results

**Discord Bot Scale-to-Zero Incompatibility (Investigation Completed):**

After thorough analysis (documented in Issue #23), scale-to-zero was determined to be **incompatible** with Discord bot architecture:

- ❌ **WebSocket Connection Loss**: Discord bots require persistent connections; scale-to-zero breaks this
- ❌ **Message Loss**: Commands sent while scaled-down are permanently lost (Discord doesn't queue)
- ❌ **User Experience**: Bot appears offline during scaled periods
- ❌ **No Auto-Wake**: Discord messages cannot trigger Cloud Run startup

**Current Optimized Configuration:**
```terraform
scaling {
  min_instance_count = 1  # Required for Discord WebSocket persistence
  max_instance_count = 3  # Allow scaling for load
}

resources {
  limits = {
    memory = "256Mi"  # Reduced for cost optimization
    cpu    = "500m"   # Sufficient for Discord bot processing
  }
}
```

**Actual Cost Reduction:** ~50-60% savings (primarily from PostgreSQL → SQLite migration)
