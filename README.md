# AI Agents

Multi-tenant AI enhancement platform for MSP technicians. This system receives webhook requests from ServiceDesk Plus, enriches tickets with context gathered from multiple sources, and returns enhanced ticket information for improved support workflows.

## Prerequisites

- **Python 3.12+** (required for all dependencies)
- **Docker Desktop** (for running PostgreSQL and Redis locally)
- **Git** (for version control)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "AI Ops"
```

### 2. Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

This installs:
- Core dependencies (FastAPI, SQLAlchemy, Celery, Redis, etc.)
- Development tools (pytest, black, ruff, mypy)

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and configure the following variables:
- `AI_AGENTS_DATABASE_URL` - PostgreSQL connection string
- `AI_AGENTS_REDIS_URL` - Redis connection string
- `AI_AGENTS_CELERY_BROKER_URL` - Celery broker URL (Redis)
- `AI_AGENTS_ENVIRONMENT` - Environment name (development/staging/production)
- `AI_AGENTS_LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

### 5. Start Infrastructure Services

**Note:** Docker configuration will be available in Story 1.2.

```bash
# Future: docker-compose up -d
```

### 6. Run Database Migrations

**Note:** Database setup will be available in Story 1.3.

```bash
# Future: alembic upgrade head
```

### 7. Run the Application

**Note:** Full application startup will be implemented in upcoming stories.

```bash
# Future: uvicorn src.main:app --reload
```

## Project Structure

```
AI Ops/
├── src/                    # Application source code
│   ├── api/               # FastAPI endpoints and middleware
│   ├── database/          # SQLAlchemy models and session management
│   ├── cache/             # Redis client and caching utilities
│   ├── services/          # Business logic and service layer
│   ├── workers/           # Celery tasks and worker configuration
│   ├── enhancement/       # LangGraph workflow and context gatherers
│   ├── monitoring/        # Prometheus metrics instrumentation
│   ├── utils/             # Cross-cutting concerns (logging, exceptions)
│   └── schemas/           # Pydantic models for validation
├── tests/                 # Test suite
│   ├── unit/             # Fast, isolated unit tests
│   ├── integration/      # Multi-component integration tests
│   └── conftest.py       # Shared pytest fixtures
├── docs/                  # Documentation
│   ├── architecture.md   # Architecture decisions and patterns
│   ├── PRD.md           # Product requirements document
│   └── epics.md         # Epic and story breakdown
├── docker/               # Dockerfiles for containerization
├── k8s/                  # Kubernetes manifests for deployment
├── alembic/              # Database migration scripts
├── pyproject.toml        # Project dependencies and configuration
├── .env.example          # Environment variable template
└── README.md            # This file
```

## Development Tools

### Code Formatting

```bash
black src/ tests/
```

### Linting

```bash
ruff check src/ tests/
```

### Type Checking

```bash
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py -v
```

## Documentation

- [Architecture Decision Document](docs/architecture.md) - System design, technology choices, and patterns
- [Product Requirements Document](docs/PRD.md) - Product vision, goals, and user stories
- [Epic Breakdown](docs/epics.md) - Detailed epic and story planning

## Contributing

**Note:** Contributing guidelines will be expanded as the project matures.

For now:
1. Follow PEP 8 style guide
2. Use type hints for all functions
3. Write unit tests for new features
4. Run `black`, `ruff`, and `mypy` before committing
5. Ensure all tests pass with `pytest`

## Current Status

**Epic 1: Foundation & Infrastructure Setup** - In Progress

This is an early-stage project. Core infrastructure and development patterns are being established in Epic 1 before implementing the enhancement workflow in Epic 2.

## License

**Note:** License information to be added.
