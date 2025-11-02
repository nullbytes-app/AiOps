# Task Completion Checklist

When completing ANY task on this project, follow these steps:

## Code Quality Gates (REQUIRED)
Before committing code:
1. **Format with Black**
   ```bash
   black src/ tests/
   ```
   - Target Python 3.12
   - Line length: 100 characters
   - Must run successfully with no warnings

2. **Lint with Ruff**
   ```bash
   ruff check --fix src/ tests/
   ```
   - Rules: E, F, I, N, W (imports, formatting, naming, etc.)
   - Must fix all issues or document exceptions

3. **Type Check with Mypy**
   ```bash
   mypy src/ --ignore-missing-imports
   ```
   - Strict mode enabled
   - All functions must have type hints
   - No `Any` unless absolutely necessary

4. **Run Tests**
   ```bash
   pytest tests/ -v --cov=src --cov-fail-under=80
   ```
   - Minimum 80% code coverage (CI enforces this)
   - All tests must pass
   - Add tests for new features (at least 3 per feature)

## Testing Requirements (MANDATORY)
For any new code:
- Write unit tests in `tests/unit/`
- Write integration tests if it touches database/Redis/Celery
- Test expected behavior, edge cases, and failure cases
- Update existing tests if logic changes
- Async tests need `@pytest.mark.asyncio` decorator
- Use fixtures from `conftest.py` when available

## Documentation
- Update docstrings (Google style)
- Add inline comments for non-obvious logic
- Update `README.md` if setup/usage changes
- Document configuration changes in `.env.example`
- Add type hints to all functions

## Git Workflow
1. Create feature branch: `git checkout -b feature/story-id-description`
2. Make changes incrementally with atomic commits
3. Run all quality checks before each commit
4. Commit with descriptive messages
5. Push and create pull request for code review
6. All CI checks must pass before merging

## Pre-commit Verification
Run this before pushing:
```bash
# All-in-one quality check
docker-compose exec api bash -c "black src/ tests/ && \
  ruff check --fix src/ tests/ && \
  mypy src/ && \
  pytest tests/ --cov=src --cov-fail-under=80"
```

## Common Tasks

### When modifying database models:
1. Update `src/database/models.py`
2. Create migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Test migration: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
5. Run database integration tests

### When adding new endpoints:
1. Define Pydantic schema in `src/schemas/`
2. Implement route in `src/api/`
3. Add service logic if needed in `src/services/`
4. Write unit tests for endpoint
5. Write integration tests for end-to-end flow
6. Update Swagger docs if needed (FastAPI auto-generates)

### When creating new Celery tasks:
1. Define task in `src/workers/tasks.py`
2. Add to Celery app configuration
3. Write unit tests for task logic
4. Write integration tests for task execution
5. Test with: `docker-compose exec worker celery -A src.workers.celery_app inspect registered`

### When updating configuration:
1. Add to `.env.example` with description
2. Update `src/config.py` Pydantic model
3. Update `README.md` environment variable table
4. Document in validation docstrings

## CI/CD Pipeline
- All changes go through GitHub Actions on PR
- Must pass: formatting, linting, type checking, tests
- Must maintain 80%+ code coverage
- Docker images built and tagged on merge to main
- Kubernetes deployment available after main merge

## Documentation Updates
- Update `README.md` for user-facing changes
- Update architecture docs for design decisions
- Update `CONTRIBUTING.md` for process changes
- Keep `docs/` folder organized by epic/feature

## Final Review Checklist
Before marking task as "Done":
- [ ] All code formatted with Black
- [ ] All linting issues fixed with Ruff
- [ ] Type checking passes with Mypy (no `Any` abuse)
- [ ] All tests pass (80%+ coverage)
- [ ] New tests written for new features
- [ ] Docstrings added to all functions
- [ ] Async/await properly handled
- [ ] No hardcoded values (use config/env vars)
- [ ] Error handling implemented
- [ ] Documentation updated
- [ ] Git history is clean
- [ ] CI/CD pipeline passes
