# Issue Tracking Framework

This directory contains systematically documented issues for the DisPinMap
project, organized for easy prioritization and tracking.

## File Naming Convention

All issues follow the format: `<priority>-<type>-<short-description>.md`

### Priority Levels (0-3)

- **0**: Critical - System breaking, production down, data loss
- **1**: High - Major functionality broken, security issues, performance
  problems
- **2**: Medium - Important features not working, notable bugs, usability issues
- **3**: Low - Minor bugs, enhancements, documentation updates

### Issue Types

- **bug**: Defects in existing functionality
- **feature**: New functionality or capabilities
- **docs**: Documentation improvements or additions
- **chore**: Maintenance tasks, refactoring, technical debt

## Example File Names

- `0-bug-monitoring-loop-not-starting.md` - Critical bug
- `1-bug-duplicate-notifications-on-startup.md` - High priority bug
- `2-feature-add-location-search.md` - Medium priority feature
- `3-docs-update-api-documentation.md` - Low priority documentation

## Issue File Structure

Each issue file should contain:

```markdown
# Issue Title

**Priority**: [0-3] **Type**: [bug|feature|docs|chore] **Status**:
[open|in-progress|blocked|closed] **Assignee**: [optional] **Created**: [date]
**Updated**: [date]

## Description

Clear description of the issue, bug, or feature request.

## Reproduction Steps (for bugs)

1. Step by step instructions
2. To reproduce the issue
3. Expected vs actual behavior

## Acceptance Criteria (for features)

- [ ] Specific deliverable 1
- [ ] Specific deliverable 2
- [ ] Testing requirements

## Technical Details

- Code locations involved
- Dependencies or related issues
- Potential solutions or approaches

## Notes

Additional context, related discussions, or implementation notes.
```

## Directory Structure

```
docs/issues/
├── CLAUDE.md                           # This documentation
├── <priority>-<type>-<description>.md  # Open issues
└── closed/                            # Resolved issues archive
    └── <priority>-<type>-<description>.md
```

## Workflow

1. **Create Issue**: Document problems/features as they're discovered
2. **Prioritize**: Assign appropriate priority and type
3. **Track Progress**: Update status as work progresses
4. **Close**: Update status to 'closed' and move file to `closed/` directory
5. **Archive**: Use `closed/` directory to maintain history of resolved issues

## Priority Guidelines

### Priority 0 (Critical)

- Production system down
- Data corruption or loss
- Security vulnerabilities
- Core functionality completely broken

### Priority 1 (High)

- Major features not working
- Performance issues affecting users
- Monitoring/alerting failures
- High-impact bugs

### Priority 2 (Medium)

- Minor feature bugs
- Usability improvements
- Non-critical performance issues
- Documentation gaps

### Priority 3 (Low)

- Cosmetic issues
- Code organization
- Nice-to-have features
- Non-urgent documentation

## Integration with Development

- Reference issues in commit messages:
  `git commit -m "fix: resolve startup duplicates (refs 1-bug-startup-duplicates)"`
- Link to issues in PR descriptions
- Update issue status when work begins/completes
- Use issue analysis to guide development priorities

## Closing and Archiving Issues

### When to Close an Issue

- **Bug fixed**: Code changes resolve the reported problem
- **Feature implemented**: All acceptance criteria are met
- **No longer relevant**: Issue became obsolete due to other changes
- **Duplicate**: Issue already covered by another issue

### Closing Process

1. Update issue status to `closed` in the header
2. Add resolution details to the issue description
3. Move file to `closed/` directory: `git mv issue.md closed/`
4. Reference the closing commit in issue resolution notes

### Example Closure

```markdown
**Status**: closed **Resolved**: 2025-07-05 **Resolution**: Fixed in commit abc123

## Resolution

Issue resolved by implementing Discord.py command processing in console interface.
All commands now work correctly through `bot.process_commands()` integration.
```

## AI Agent Guidelines

When working on this project:

1. **Check existing issues** before starting work
2. **Create new issues** for discovered problems
3. **Update issue status** as work progresses
4. **Reference issues** in commits and PRs
5. **Close and archive** resolved issues properly
6. **Prioritize work** based on issue priorities
