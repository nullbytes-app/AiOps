# Story 1.1: Initialize Project Structure and Development Environment

Status: ready-for-dev

## Story

As a developer,
I want a well-organized project structure with Python dependencies managed,
so that I can start building features with a solid foundation.

## Acceptance Criteria

1. Project directory structure created following Python best practices (src/, tests/, docs/, docker/, k8s/)
2. Python 3.12+ virtual environment configured
3. Core dependencies installed (FastAPI, LangGraph, SQLAlchemy, Redis client, pytest)
4. requirements.txt and/or pyproject.toml file created
5. .gitignore configured for Python projects
6. README.md with initial setup instructions
7. All dependencies install successfully with `pip install -r requirements.txt`

[Source: docs/epics.md#Story-1.1, docs/tech-spec-epic-1.md#Acceptance-Criteria]

## Tasks / Subtasks

- [ ] **Task 1: Create project directory structure** (AC: #1)
  - [ ] Create root project directory structure with folders: src/, tests/, docs/, docker/, k8s/, alembic/
  - [ ] Create src/ subdirectories: api/, database/, cache/, services/, workers/, enhancement/, monitoring/, utils/, schemas/
  - [ ] Create tests/ subdirectories: unit/, integration/, conftest.py
  - [ ] Create docs/ with initial files: architecture.md (existing), PRD.md (existing), epics.md (existing)
  - [ ] Create docker/ directory for Dockerfiles
  - [ ] Create k8s/ directory for Kubernetes manifests
  - [ ] Add __init__.py files to all Python package directories

- [ ] **Task 2: Initialize Python dependency management** (AC: #2, #3, #4)
  - [ ] Create pyproject.toml with project metadata and dependencies
  - [ ] Define core dependencies with versions:
    - fastapi>=0.104.0
    - uvicorn[standard]>=0.24.0
    - pydantic>=2.5.0
    - pydantic-settings>=2.1.0
    - sqlalchemy[asyncio]>=2.0.23
    - alembic>=1.12.1
    - asyncpg>=0.29.0
    - redis>=5.0.1
    - celery[redis]>=5.3.4
    - httpx>=0.25.2
    - loguru>=0.7.2
  - [ ] Define dev dependencies: pytest>=7.4.3, pytest-asyncio>=0.21.1, black>=23.11.0, ruff>=0.1.6, mypy>=1.7.1
  - [ ] Create virtual environment: `python3.12 -m venv venv`
  - [ ] Test dependency installation: `pip install -e .`

- [ ] **Task 3: Configure .gitignore** (AC: #5)
  - [ ] Create .gitignore with Python-specific entries
  - [ ] Add entries: .env, __pycache__/, *.pyc, *.pyo, venv/, .venv/, .pytest_cache/, .mypy_cache/, .ruff_cache/
  - [ ] Add: *.db, *.sqlite, .DS_Store, .idea/, .vscode/
  - [ ] Add: alembic/versions/*.py (exclude migration files initially, uncomment when ready)
  - [ ] Verify .env is git-ignored

- [ ] **Task 4: Create README.md with setup instructions** (AC: #6)
  - [ ] Add project title and description
  - [ ] Document prerequisites: Python 3.12+, Docker Desktop, Git
  - [ ] Document local setup steps:
    1. Clone repository
    2. Create virtual environment
    3. Install dependencies
    4. Copy .env.example to .env
    5. Run docker-compose up (future story)
  - [ ] Add project structure overview
  - [ ] Add links to docs/ folder for architecture and PRD
  - [ ] Add placeholder for contributing guidelines

- [ ] **Task 5: Create environment configuration template** (AC: #7)
  - [ ] Create .env.example with template variables
  - [ ] Add database URL: AI_AGENTS_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ai_agents
  - [ ] Add Redis URL: AI_AGENTS_REDIS_URL=redis://localhost:6379/0
  - [ ] Add Celery broker: AI_AGENTS_CELERY_BROKER_URL=redis://localhost:6379/1
  - [ ] Add environment: AI_AGENTS_ENVIRONMENT=development
  - [ ] Add log level: AI_AGENTS_LOG_LEVEL=INFO
  - [ ] Document each variable with comments

- [ ] **Task 6: Initialize configuration module** (AC: #3)
  - [ ] Create src/config.py with Pydantic Settings class
  - [ ] Define Settings with fields: database_url, redis_url, celery_broker_url, environment, log_level
  - [ ] Configure env_prefix = "AI_AGENTS_"
  - [ ] Set defaults for pool sizes and connection limits
  - [ ] Export settings instance for import by other modules

- [ ] **Task 7: Create initial placeholder modules** (AC: #1)
  - [ ] Create src/main.py with minimal FastAPI app initialization
  - [ ] Create src/database/__init__.py, src/database/models.py (placeholder)
  - [ ] Create src/cache/__init__.py, src/cache/redis_client.py (placeholder)
  - [ ] Create src/api/__init__.py, src/api/health.py (placeholder)
  - [ ] Create src/workers/__init__.py, src/workers/celery_app.py (placeholder)
  - [ ] Create src/utils/__init__.py, src/utils/logger.py (placeholder)

- [ ] **Task 8: Write unit tests for configuration** (AC: #7)
  - [ ] Create tests/unit/test_config.py
  - [ ] Test Settings loads from environment variables
  - [ ] Test Settings uses defaults when env vars missing
  - [ ] Test env_prefix correctly prepends to variable names
  - [ ] Run tests with pytest: `pytest tests/unit/test_config.py -v`

- [ ] **Task 9: Validation and documentation** (AC: #7)
  - [ ] Verify all dependencies install without errors
  - [ ] Verify project structure matches architecture.md specification
  - [ ] Verify .gitignore prevents .env from being committed
  - [ ] Test README instructions: new developer can follow and set up project
  - [ ] Commit initial project structure to git

## Dev Notes

### Architecture Alignment

This story implements the foundational project structure defined in architecture.md, establishing the following components:

**Directory Structure:**
- `src/` - Application source code organized by component (api, database, workers, etc.)
- `tests/` - Unit and integration tests mirroring src/ structure
- `docs/` - Architecture, PRD, and epic documentation (already exists)
- `docker/` - Dockerfiles for containerization (Story 1.2)
- `k8s/` - Kubernetes manifests (Story 1.6)
- `alembic/` - Database migrations (Story 1.3)

**Dependency Management:**
- Using pyproject.toml (modern Python standard) instead of requirements.txt
- All versions match architecture.md Decision Summary table
- Python 3.12 (stable, supported until 2028)
- FastAPI 0.104+ for async API framework
- SQLAlchemy 2.0+ with asyncpg for async database operations
- Celery 5.x with Redis broker for distributed task processing

**Configuration Pattern:**
- Pydantic Settings for type-safe configuration
- Environment variables with AI_AGENTS_ prefix for namespace isolation
- .env file for local development (git-ignored)
- Kubernetes Secrets for production (future story)

**Code Quality Standards:**
- Black for code formatting
- Ruff for linting (faster replacement for Flake8)
- Mypy for static type checking
- Pytest for testing framework

### Project Structure Notes

**Naming Conventions (per architecture.md):**
- Files/modules: snake_case (e.g., `redis_client.py`)
- Classes: PascalCase (e.g., `Settings`, `RedisClient`)
- Functions/variables: snake_case (e.g., `get_async_session`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_ATTEMPTS`)
- Environment variables: UPPER_SNAKE_CASE with AI_AGENTS_ prefix

**Module Organization:**
- src/api/ - FastAPI endpoints and middleware
- src/database/ - SQLAlchemy models and session management
- src/cache/ - Redis client and caching utilities
- src/services/ - Business logic and service layer
- src/workers/ - Celery tasks and worker configuration
- src/enhancement/ - LangGraph workflow and context gatherers (Epic 2)
- src/monitoring/ - Prometheus metrics (Epic 4)
- src/utils/ - Cross-cutting concerns (logging, exceptions)
- src/schemas/ - Pydantic models for validation

### Testing Strategy

**Unit Tests:**
- Test configuration loading with different environment variables
- Test default values are applied correctly
- Mock external dependencies (database, Redis)
- Aim for 80% code coverage (per architecture.md)

**Integration Tests:**
- Deferred to Story 1.2+ when services are containerized
- Will test full stack: API → Database → Redis → Workers

**Test File Organization:**
- tests/unit/ - Fast, isolated unit tests
- tests/integration/ - Multi-component integration tests
- tests/conftest.py - Shared pytest fixtures

### Dependencies Rationale

**Core Application:**
- **FastAPI**: Async web framework with automatic OpenAPI docs
- **Uvicorn**: ASGI server for running FastAPI
- **Pydantic**: Data validation (included with FastAPI)
- **Pydantic Settings**: Environment-based configuration

**Database:**
- **SQLAlchemy 2.0+**: Async ORM with modern API
- **Alembic**: Database migration tool (industry standard)
- **asyncpg**: Fast async PostgreSQL driver

**Message Queue:**
- **Redis**: Broker for Celery + caching layer
- **Celery**: Distributed task queue

**HTTP Client:**
- **HTTPX**: Modern async HTTP client (will be used in Epic 2 for ServiceDesk Plus API)

**Logging:**
- **Loguru**: Simple, powerful logging library

**Development:**
- **Pytest**: Testing framework with async support
- **Black**: Code formatter
- **Ruff**: Fast Python linter
- **Mypy**: Static type checker

### Constraints and Considerations

1. **Python Version:** Must use 3.12+ (architecture requirement)
   - Security support until 2028
   - Good library ecosystem compatibility

2. **Virtual Environment:** Required for dependency isolation
   - Use venv (standard library) rather than conda/poetry
   - Activate before installing dependencies

3. **Git Workflow:**
   - .env MUST be git-ignored (contains sensitive data)
   - .env.example provides template for developers
   - Never commit API keys or passwords

4. **File Paths:**
   - All paths must work cross-platform (Windows, macOS, Linux)
   - Use pathlib for path manipulation
   - Avoid hardcoded absolute paths

5. **Future Extensibility:**
   - Structure supports future epics (Epic 2: enhancement logic, Epic 3: multi-tenancy, etc.)
   - Placeholder modules created for upcoming features
   - README will be updated in Story 1.8 with full documentation

### References

- [Source: docs/architecture.md#Project-Structure]
- [Source: docs/architecture.md#Technology-Stack-Details]
- [Source: docs/architecture.md#Implementation-Patterns]
- [Source: docs/tech-spec-epic-1.md#Detailed-Design]
- [Source: docs/tech-spec-epic-1.md#Dependencies-and-Integrations]
- [Source: docs/epics.md#Story-1.1]

### Change Log

- 2025-11-01: Story created (Ravi, SM Agent)

## Dev Agent Record

### Context Reference

- Story Context XML: `docs/stories/1-1-initialize-project-structure-and-development-environment.context.xml`

### Agent Model Used

_To be filled by dev agent during implementation_

### Debug Log References

_To be filled by dev agent during implementation_

### Completion Notes List

_To be filled by dev agent during implementation_

### File List

_To be filled by dev agent during implementation_
