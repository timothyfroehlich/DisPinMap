#!/bin/bash
#
# Comprehensive test, lint, and format checker for DisPinMap
#
# This script runs all code quality checks and provides a summary with fix commands.
# Designed to be run from the project root directory.
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Tracking variables
PASSED_CHECKS=()
FAILED_CHECKS=()
FIX_COMMANDS=()

echo -e "${BLUE}🚀 Running comprehensive code quality checks...${NC}"
echo "=================================================="

# Function to run a check and track results
run_check() {
    local name="$1"
    local command="$2"
    local fix_command="$3"
    
    echo -e "\n${BLUE}Running: ${name}${NC}"
    echo "Command: $command"
    
    if eval "$command"; then
        echo -e "${GREEN}✅ $name: PASSED${NC}"
        PASSED_CHECKS+=("$name")
    else
        echo -e "${RED}❌ $name: FAILED${NC}"
        FAILED_CHECKS+=("$name")
        if [ -n "$fix_command" ]; then
            FIX_COMMANDS+=("$fix_command")
        fi
    fi
}

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found at venv/bin/activate${NC}"
    echo "Please create it with: python -m venv venv && source venv/bin/activate && pip install -e .[dev]"
    exit 1
fi

# Check Python version
echo -e "\n${BLUE}🐍 Python version:${NC}"
python --version

# Install/upgrade dependencies
echo -e "\n${BLUE}📦 Ensuring dependencies are up to date...${NC}"
pip install -e .[dev] --quiet

echo -e "\n${BLUE}Starting quality checks...${NC}"
echo "=========================================="

# 1. Python syntax check
run_check "Python Syntax Check" \
    "python -m py_compile src/**/*.py" \
    ""

# 2. Ruff linting
run_check "Ruff Linting" \
    "ruff check ." \
    "ruff check --fix ."

# 3. Ruff formatting check
run_check "Ruff Format Check" \
    "ruff format --check ." \
    "ruff format ."

# Note: Ruff handles all Python linting, formatting, type checking, and import sorting
# We do not use mypy, black, flake8, or isort - Ruff is our single tool for Python code quality

# 4. Prettier formatting check (markdown/yaml)
run_check "Prettier Format Check" \
    "prettier --check \"**/*.{md,yml,yaml}\" --ignore-path .gitignore" \
    "prettier --write \"**/*.{md,yml,yaml}\" --ignore-path .gitignore"

# 5. Security check (if bandit is available)
if command -v bandit >/dev/null 2>&1; then
    run_check "Bandit Security Check" \
        "bandit -r src/ -f json --quiet" \
        ""
else
    echo -e "${YELLOW}⚠️ Bandit not installed, skipping security check${NC}"
fi

# 6. Tests with coverage
run_check "Test Suite with Coverage" \
    "pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=60 -v" \
    ""

# 7. Integration tests (if they exist and are separate)
if [ -d "tests/integration" ]; then
    run_check "Integration Tests" \
        "pytest tests/integration/ -v" \
        ""
fi

# 8. Documentation tests (if doctest files exist, excluding local_dev)
if find src/ -name "*.py" -not -path "src/local_dev/*" -exec grep -l "doctest" {} \; | head -1 > /dev/null; then
    run_check "Documentation Tests" \
        "find src/ -name '*.py' -not -path 'src/local_dev/*' -exec python -m doctest {} \;" \
        ""
fi

# Summary Report
echo -e "\n\n${BLUE}=================================================="
echo "🏁 QUALITY CHECK SUMMARY"
echo -e "==================================================${NC}"

echo -e "\n${GREEN}✅ PASSED CHECKS (${#PASSED_CHECKS[@]}):${NC}"
for check in "${PASSED_CHECKS[@]}"; do
    echo "   • $check"
done

if [ ${#FAILED_CHECKS[@]} -gt 0 ]; then
    echo -e "\n${RED}❌ FAILED CHECKS (${#FAILED_CHECKS[@]}):${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "   • $check"
    done
    
    if [ ${#FIX_COMMANDS[@]} -gt 0 ]; then
        echo -e "\n${YELLOW}🔧 AUTO-FIX COMMANDS:${NC}"
        echo "Run these commands to automatically fix issues:"
        echo ""
        for cmd in "${FIX_COMMANDS[@]}"; do
            echo -e "   ${YELLOW}$cmd${NC}"
        done
        echo ""
        echo "Then re-run this script to verify fixes."
    fi
    
    echo -e "\n${RED}❌ Some checks failed. Please fix the issues above.${NC}"
    exit 1
else
    echo -e "\n${GREEN}🎉 ALL CHECKS PASSED! Code is ready for commit.${NC}"
    
    # Bonus: Show test coverage summary
    echo -e "\n${BLUE}📊 COVERAGE SUMMARY:${NC}"
    pytest tests/ --cov=src --cov-report=term --quiet | tail -1
    
    # Show git status
    echo -e "\n${BLUE}📋 GIT STATUS:${NC}"
    git status --porcelain | head -10
    if [ $(git status --porcelain | wc -l) -gt 10 ]; then
        echo "... and $(( $(git status --porcelain | wc -l) - 10 )) more files"
    fi
    
    exit 0
fi