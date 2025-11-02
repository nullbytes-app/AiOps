# Code Style & Conventions

## Python & PEP8
- **Python Version:** 3.12+
- **Code Style:** PEP8 compliant
- **Auto-formatter:** Black (line-length=100)
- **Linter:** Ruff (E, F, I, N, W rules)
- **Type Checker:** Mypy (strict mode enabled)

## Type Hints & Documentation
- **Required:** Type hints for all function parameters and return values
- **Docstrings:** Google style for all functions, classes, modules
- **Example:**
  ```python
  def process_ticket(ticket_id: str) -> dict[str, Any]:
      """
      Process an enhancement ticket asynchronously.

      Args:
          ticket_id (str): Unique identifier for the ticket.

      Returns:
          dict[str, Any]: Processed ticket with enhancement data.
      """
  ```

## Naming Conventions
- **Variables/Functions:** snake_case
- **Classes:** PascalCase
- **Constants:** UPPER_SNAKE_CASE
- **Private Methods:** _leading_underscore
- **Modules:** lowercase with underscores (avoid hyphens)

## Code Organization
- **Max file length:** 500 lines of code
- **Organize by feature:** Group related classes/functions together
- **Clear imports:** Use relative imports within packages
- **Separation of concerns:**
  - `agent.py` - Main agent definition & execution
  - `tools.py` - Tool functions
  - `prompts.py` - System prompts
  - `schemas.py` - Data validation models
  - `services.py` - Business logic

## Testing Requirements
- **Framework:** Pytest with pytest-asyncio
- **Async Tests:** Use `@pytest.mark.asyncio` decorator
- **Coverage Minimum:** 80% (CI/CD enforces this)
- **Test Organization:**
  - `tests/unit/` - Fast isolated tests
  - `tests/integration/` - Multi-component tests
  - `tests/conftest.py` - Shared fixtures
- **Per Feature:** At least 3 tests:
  - 1 expected use case
  - 1 edge case
  - 1 failure case

## Database & Migrations
- **ORM:** SQLAlchemy 2.0 async
- **Migrations:** Alembic (auto-applied on Docker startup)
- **Multi-tenancy:** Row-Level Security (RLS) policies
- **Tenant Isolation:** `current_setting('app.current_tenant_id')`
- **Models:** In `src/database/models.py`
- **Sessions:** Via `async_session_maker` in `src/database/session.py`

## Configuration Management
- **Pydantic v2 Settings:** In `src/config.py`
- **Environment Prefix:** `AI_AGENTS_` (required for all env vars)
- **Sensitive Data:** Never commit `.env` files
- **Example:** `AI_AGENTS_DATABASE_URL`, `AI_AGENTS_REDIS_URL`

## Logging & Monitoring
- **Logger:** loguru (structured, colored output)
- **Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Context:** Include task_id, tenant_id, request_id
- **Production:** JSON serialization for log aggregation

## Async & Concurrency
- **Async I/O:** FastAPI is async-first (use `async def`)
- **Database:** Async SQLAlchemy with connection pooling (default: 20)
- **Redis:** Async redis-py client (max 10 connections)
- **Celery:** Async task execution (4 workers, 1 prefetch)
- **No Blocking Calls:** Never use `.run_until_complete()`, `time.sleep()`, etc.
