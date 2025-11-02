# Suggested Commands for Development

## Docker & Container Management
```bash
# Start all services (recommended for development)
docker-compose up -d

# Stop all services (keep data)
docker-compose down

# Remove everything (fresh start)
docker-compose down -v

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api      # or postgres, redis, worker
docker-compose logs -f worker

# Check service health
docker-compose ps
```

## Running Tests
```bash
# Inside Docker (recommended)
docker-compose exec api pytest

# With coverage report
docker-compose exec api pytest --cov=src --cov-report=html

# Run specific test file
docker-compose exec api pytest tests/unit/test_config.py -v

# Run specific test class
docker-compose exec api pytest tests/integration/test_celery_tasks.py::TestCeleryTaskExecution -v

# Locally (requires .venv and services running)
pytest tests/ -v
pytest tests/ --cov=src --cov-fail-under=80
```

## Code Quality & Formatting
```bash
# Auto-format code (required before committing)
black src/ tests/

# Check linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Type checking
mypy src/ --ignore-missing-imports

# Run all quality checks (inside Docker)
docker-compose exec api bash -c "black src/ tests/ && ruff check --fix src/ tests/ && mypy src/"
```

## Database Migrations
```bash
# Apply all pending migrations (inside Docker)
docker-compose exec api alembic upgrade head

# Check current migration status
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history

# Create new migration (after updating models.py)
alembic revision --autogenerate -m "Description of changes"

# Rollback one migration (testing only)
docker-compose exec api alembic downgrade -1
```

## Redis & Queue Management
```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Check queue depth
docker-compose exec redis redis-cli LLEN enhancement:queue

# View next 10 jobs in queue
docker-compose exec redis redis-cli LRANGE enhancement:queue 0 9

# Clear queue (development only)
docker-compose exec redis redis-cli DEL enhancement:queue

# View Redis stats
docker-compose exec redis redis-cli INFO
```

## Celery Worker Management
```bash
# Start worker (inside Docker)
docker-compose up -d worker

# View worker logs
docker-compose logs -f worker

# Ping worker
docker-compose exec worker celery -A src.workers.celery_app inspect ping

# List active tasks
docker-compose exec worker celery -A src.workers.celery_app inspect active

# View registered tasks
docker-compose exec worker celery -A src.workers.celery_app inspect registered

# View worker stats
docker-compose exec worker celery -A src.workers.celery_app inspect stats

# Purge all tasks (development only)
docker-compose exec worker celery -A src.workers.celery_app purge
```

## API & Health Checks
```bash
# Health check endpoint
curl http://localhost:8000/health

# Swagger UI
open http://localhost:8000/docs

# Direct API access
curl -X GET http://localhost:8000/api/v1/health
```

## Git & Commit Management
```bash
# Check status
git status

# View recent commits
git log --oneline -10

# View changes
git diff
git diff --staged

# Create commit
git add .
git commit -m "Your message"

# Push to remote
git push origin main
```

## Local Development (Without Docker)
```bash
# Activate virtual environment
source venv/bin/activate  # or .venv/bin/activate

# Load environment variables
set -a && source .env && set +a

# Install/update dependencies
pip install -e ".[dev]"

# Run FastAPI
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info --concurrency=4

# Run tests locally
pytest tests/ -v --asyncio-mode=auto
```

## Kubernetes Deployment
```bash
# Deploy to local Kubernetes cluster
./k8s/test-deployment.sh

# Check pods
kubectl get pods -n ai-agents

# View logs
kubectl logs -n ai-agents deployment/api -f

# Port forward
kubectl port-forward -n ai-agents svc/api 8000:8000

# Delete deployment
kubectl delete namespace ai-agents
```

## Troubleshooting
```bash
# Check what's using a port
lsof -i :8000  # or :5433, :6379

# Database connectivity test
docker-compose exec postgres pg_isready -U aiagents

# Redis connectivity test
docker-compose exec redis redis-cli ping

# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```
