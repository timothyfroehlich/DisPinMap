# Contributing to Discord Pinball Map Bot

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate`
4. Install dependencies: `pip install -e .[dev]`
5. Install pre-commit hooks: `pre-commit install`

## Code Style

- We use Ruff for code formatting and linting (line length: 88)
- We use Prettier for markdown and YAML formatting

## Testing

- Run tests: `pytest`
- Run tests with coverage: `pytest --cov=src --cov-report=html`
- View coverage report: Open `htmlcov/index.html`

## Pre-commit Hooks

Before committing, the following checks will run automatically:

- Code formatting (Ruff)
- Linting (Ruff)
- Markdown/YAML formatting (Prettier)
- Basic file checks (trailing whitespace, etc.)

## VS Code Integration

This project includes VS Code settings for:

- Automatic formatting on save (using Ruff)
- Test discovery
- Recommended extensions
- Useful tasks (Run bot, tests, formatting, etc.)

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Run tests locally
4. Ensure pre-commit hooks pass
5. Submit a pull request
