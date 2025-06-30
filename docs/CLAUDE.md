# Documentation Agent Instructions

## Documentation Structure
- **DEVELOPER_HANDBOOK.md** - Complete development guide and architecture
- **DATABASE.md** - Schema documentation and database patterns
- **simulation-testing-framework.md** - Advanced testing concepts

## Writing Standards
**For technical documentation:**
- Include prerequisites and setup steps
- Provide working code examples with syntax highlighting
- Add troubleshooting sections for common issues
- Use consistent formatting and structure

**For user-facing guides:**
- Start with simple examples, build complexity gradually
- Include command reference with clear explanations
- Use bullet points and numbered lists for clarity
- Test all examples to ensure they work

## Documentation Maintenance
```bash
# Verify examples still work
python -c "import src.main"  # Check imports
pytest tests/integration/   # Verify workflows

# Check for outdated references
grep -r "!command" docs/     # Should use current prefix
grep -r "target_data" docs/  # Should use location_id
```

## Cross-References
**IMPORTANT**: When updating code, check these docs for references:
- Command prefix changes affect USER_DOCUMENTATION.md
- Database schema changes affect DATABASE.md and DEVELOPER_HANDBOOK.md
- New features need examples in USER_DOCUMENTATION.md
- Architecture changes need DEVELOPER_HANDBOOK.md updates

## Agent-Specific Guidelines
**For CLAUDE.md files:**
- Keep concise but comprehensive
- Focus on critical patterns and current issues
- Include common commands and troubleshooting
- Reference external docs rather than duplicating content
- Use clear headings and bullet points for scanning

## Style Guide
- **Headers**: Use descriptive, scannable titles
- **Code blocks**: Always specify language for syntax highlighting
- **Commands**: Show both the command and expected output when helpful
- **Cross-links**: Use relative paths for internal documentation
- **Examples**: Prefer real, working examples over pseudocode
