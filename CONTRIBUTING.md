# Contributing Guidelines

This document outlines the development workflow, code standards, and contribution process for the AI Agents project.

## Table of Contents

- [Development Workflow](#development-workflow)
- [Code Style Requirements](#code-style-requirements)
- [Testing Requirements](#testing-requirements)
- [Running Code Quality Checks](#running-code-quality-checks)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Process](#pull-request-process)
- [Pre-commit Hooks (Optional)](#pre-commit-hooks-optional)
- [Adding New Dependencies](#adding-new-dependencies)
- [Project Development Methodology](#project-development-methodology)
- [Getting Help](#getting-help)

## Development Workflow

### 1. Fork and Clone the Repository

```bash
# Fork the repository on GitHub (for external contributors)
# Clone your fork
git clone https://github.com/YOUR-USERNAME/AI-Ops.git
cd AI\ Ops

# For maintainers: clone directly
git clone https://github.com/nullBytes/AI-Ops.git
cd AI\ Ops
```

### 2. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch (see branch naming convention below)
git checkout -b feature/short-description
# or
git checkout -b bugfix/issue-description
```

### 3. Set Up Development Environment

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env

# Start Docker services (recommended)
docker-compose up -d
```

### 4. Make Code Changes

- Create new features or fix bugs in appropriate modules
- Follow code style requirements (see below)
- Add or update tests as needed
- Write clear, descriptive commit messages

### 5. Test Your Changes

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py -v

# Run linting
ruff check src/ tests/

# Run formatting check
black --check src/ tests/

# Run type checking
mypy src/
```

### 6. Push and Create Pull Request

```bash
# Push your branch
git push origin feature/short-description

# Create Pull Request on GitHub
# Provide clear description of changes
# Link to relevant issues
# Ensure CI checks pass
```

## Code Style Requirements

All code must follow these standards. The CI/CD pipeline enforces them automatically.

### Python Style Guide: PEP 8

- Use 4 spaces for indentation (never tabs)
- Line length limit: 100 characters
- Two blank lines between top-level functions/classes
- One blank line between methods in a class
- Use lowercase with underscores for variable/function names
- Use UPPERCASE for constants

### Code Formatting: Black

Black auto-formats all Python code consistently. Never manually format code.

```bash
# Auto-format all code
black src/ tests/

# Check formatting without modifying
black --check src/ tests/

# Format specific file
black src/main.py
```

**Configuration:** Line length = 100 (defined in `pyproject.toml`)

### Linting: Ruff

Ruff catches code quality issues, unused imports, undefined variables, and security problems.

```bash
# Check for linting issues
ruff check src/ tests/

# Auto-fix common issues
ruff check --fix src/ tests/

# View detailed error messages
ruff check src/ tests/ --show-settings
```

**Enabled rules:** E (errors), F (Pyflakes), I (imports), N (naming), W (warnings)

### Type Checking: Mypy

All functions must have type hints. Mypy enforces strict type checking.

```bash
# Run type checking
mypy src/ --ignore-missing-imports

# Check specific file
mypy src/main.py

# Check in strict mode (recommended)
mypy src/ --strict
```

**Type Hints Examples:**

```python
# Function with type hints
def process_ticket(ticket_id: str, priority: int) -> dict[str, any]:
    """
    Process a ticket with given ID and priority.

    Args:
        ticket_id: Unique identifier for the ticket
        priority: Priority level (1-5)

    Returns:
        Dictionary containing processed ticket information
    """
    pass

# Class with type hints
class TicketProcessor:
    def __init__(self, database_url: str) -> None:
        self.db_url: str = database_url

    async def enhance_ticket(self, data: dict[str, str]) -> dict[str, any]:
        pass
```

## Testing Requirements

### Pytest Framework

All new code must include unit tests. Minimum coverage: **80%**.

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_config.py::test_settings_validation -v

# Run with markers
pytest -m "not slow"  # Skip slow tests
pytest -m "asyncio"   # Run only async tests
```

### Test Organization

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_config.py
│   └── test_models.py
├── integration/       # Multi-component tests
│   ├── test_database.py
│   └── test_redis_queue.py
└── conftest.py        # Shared fixtures
```

### Writing Tests

```python
import pytest
from src.config import Settings

class TestSettings:
    """Test Settings configuration."""

    def test_default_environment(self):
        """Test default environment is development."""
        settings = Settings()
        assert settings.environment == "development"

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test database connection (async test)."""
        settings = Settings()
        # Test async functionality
        pass

    @pytest.mark.parametrize("env,expected", [
        ("development", False),
        ("production", True),
    ])
    def test_debug_mode(self, env, expected):
        """Test debug mode based on environment."""
        pass
```

### Test Coverage Goals

- **Unit tests:** Cover all business logic, edge cases, and error handling
- **Integration tests:** Test component interactions and API endpoints
- **Coverage minimum:** 80% across the codebase
- **Critical code:** Aim for 100% coverage on security-related functions

## Running Code Quality Checks

### Before Committing

Always run these checks locally before committing:

```bash
# Auto-format code
black src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Type check
mypy src/ --ignore-missing-imports

# Run all tests with coverage
pytest tests/ --cov=src --cov-fail-under=80

# Run in Docker (recommended)
docker-compose exec api bash -c \
  "black src/ tests/ && \
   ruff check --fix src/ tests/ && \
   mypy src/ && \
   pytest tests/ --cov=src --cov-fail-under=80"
```

### CI/CD Pipeline Checks

The GitHub Actions pipeline runs automatically on all PRs:

1. **Black formatting** - Must pass without changes
2. **Ruff linting** - Must not report errors
3. **Mypy type checking** - Must pass with strict checking
4. **Pytest** - All tests must pass with 80%+ coverage
5. **Docker build** - Images must build successfully

## Branch Naming Convention

Use descriptive branch names that indicate the type of change:

```
feature/description-of-feature       # New feature
bugfix/issue-number-description      # Bug fix
docs/description-of-documentation    # Documentation changes
refactor/description-of-refactoring  # Code refactoring
chore/description-of-chore           # Build, dependencies, etc.
```

**Examples:**

```
feature/webhook-signature-validation
bugfix/redis-connection-timeout-issue
docs/kubernetes-deployment-guide
refactor/database-session-management
chore/update-python-dependencies
```

## Commit Message Conventions

Commit messages should be clear and descriptive. Follow this format:

```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, missing semicolons, etc.)
- `refactor:` Code refactoring without feature changes
- `test:` Adding or updating tests
- `chore:` Build, dependencies, version bumps
- `perf:` Performance improvements

**Examples:**

```
feat: implement webhook signature validation

Add support for validating ServiceDesk Plus webhook signatures
using HMAC-SHA256. Includes comprehensive test coverage for
valid and invalid signatures.

Closes #42
```

```
fix: resolve redis connection timeout on slow networks

Increase default connection timeout from 3 to 10 seconds
to handle slow network conditions. Add exponential backoff
for connection retries.

Fixes #128
```

```
docs: add environment variables reference to README

Add comprehensive table documenting all AI_AGENTS_* environment
variables with descriptions, default values, and examples.
```

## Pull Request Process

### Creating a Pull Request

1. **Push your branch** to GitHub
2. **Create PR** from your branch to `main`
3. **Fill in the PR template** with:
   - Clear description of changes
   - Related issues (use `Closes #123`)
   - Testing instructions
   - Screenshots (if UI changes)

### PR Title Format

```
[Type] Brief description of changes

Examples:
[Feature] Add webhook signature validation
[Bugfix] Fix Redis connection timeout
[Docs] Update deployment documentation
[Refactor] Simplify database session management
```

### PR Description Template

```markdown
## Description
Brief explanation of what the PR changes and why.

## Related Issues
Closes #123
Related to #456

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
How to test these changes:
1. Step 1
2. Step 2

## Screenshots (if applicable)
[Add screenshots here]

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code style checks pass (black, ruff, mypy)
- [ ] Coverage maintained above 80%
- [ ] No breaking changes or documented
```

### Code Review Process

1. **Automatic checks** - CI/CD pipeline runs all tests and quality checks
2. **Manual review** - At least one maintainer reviews the code
3. **Addressing feedback** - Update code based on review comments
4. **Re-review** - Maintainer verifies changes address feedback
5. **Merge** - PR merged after approval

### Approval Requirements

- ✅ All CI checks pass
- ✅ At least one approval from maintainer
- ✅ No unresolved conversations
- ✅ Branch up-to-date with main

## Pre-commit Hooks (Optional)

Pre-commit hooks automatically run checks before committing (optional but recommended).

### Installation

```bash
# Install pre-commit framework
pip install pre-commit

# Install git hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files
```

### Configuration

See `.pre-commit-config.yaml` (to be created) for available hooks.

## Adding New Dependencies

### Python Dependencies

Always get approval before adding new dependencies.

```bash
# Add new dependency
pip install package-name

# Update requirements
pip freeze > requirements.txt

# Or using pyproject.toml (preferred)
# Edit pyproject.toml and add under [project] dependencies
# Then reinstall
pip install -e ".[dev]"

# Test that everything still works
pytest tests/ --cov=src

# Commit the changes
git add pyproject.toml uv.lock  # or requirements.txt
git commit -m "chore: add new-package-name dependency"
```

### Docker Dependencies

Update `docker/backend.dockerfile` or `docker/celeryworker.dockerfile` as needed.

### Kubernetes Dependencies

Update Kubernetes manifests in `k8s/` directory if adding infrastructure components.

## Project Development Methodology

This project follows a **story-based development workflow** using BMAD (Build-Measure-Adapt Disciplines):

### Epic-Driven Development

1. **Epics** - Large features spanning multiple stories
2. **Stories** - Individual user-facing features with acceptance criteria
3. **Tasks** - Concrete implementation steps within a story
4. **Subtasks** - Breaking down complex tasks

### Story-Based Development Process

```
Draft Story → Context Generation → Implementation → Testing → Code Review → Done
```

### Acceptance Criteria

All stories define clear acceptance criteria that must be met before marking done:

- Functionality works as specified
- Code passes all quality checks (80%+ coverage)
- Documentation updated
- No breaking changes (or documented)

### Development Branch Names

Development follows the Epic-Story naming pattern:

```
epic-1: Foundation & Infrastructure Setup
  ├─ 1-1: Initialize Project Structure
  ├─ 1-2: Docker Configuration
  ├─ 1-3: PostgreSQL Database Setup
  └─ 1-8: Documentation

Branch names mirror this structure:
feature/1-2-docker-configuration
feature/1-8-documentation
```

## Getting Help

### Documentation

- [README.md](README.md) - Quick start and overview
- [docs/architecture.md](docs/architecture.md) - Architecture decisions
- [docs/deployment.md](docs/deployment.md) - Deployment guide
- [docs/tech-spec-epic-1.md](docs/tech-spec-epic-1.md) - Technical specifications

### Discussion & Issues

- 🐛 **Report bugs** - GitHub Issues
- 💡 **Suggest features** - GitHub Discussions
- ❓ **Ask questions** - GitHub Discussions

### Development Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

**Thank you for contributing to AI Agents! 🙌**

Questions? Open an issue or start a discussion on GitHub.
