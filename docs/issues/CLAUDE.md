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

## Workflow

1. **Create Issue**: Document problems/features as they're discovered
2. **Prioritize**: Assign appropriate priority and type
3. **Track Progress**: Update status as work progresses
4. **Close**: Move to closed status when resolved
5. **Archive**: Optionally move closed issues to subdirectories

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

## AI Agent Guidelines

When working on this project:

1. **Check existing issues** before starting work
2. **Create new issues** for discovered problems
3. **Update issue status** as work progresses
4. **Reference issues** in commits and PRs
5. **Prioritize work** based on issue priorities
