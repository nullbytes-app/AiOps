# AI Ops Project Overview

## Project Purpose
Multi-tenant AI enhancement platform for MSP technicians. System receives webhook requests from ServiceDesk Plus, enriches tickets with context gathered from multiple sources, and returns enhanced ticket information for improved support workflows.

## Tech Stack
- **Language:** Python 3.12+
- **API Framework:** FastAPI + Uvicorn
- **Database:** PostgreSQL 17 (async via asyncpg) with Alembic migrations
- **Caching/Queue:** Redis 7 (AOF persistence)
- **Task Queue:** Celery 5.x (4 concurrent workers per pod)
- **ORM:** SQLAlchemy 2.0 with async support
- **Data Validation:** Pydantic v2
- **Security:** HMAC-SHA256 webhook validation
- **Monitoring:** Structured logging via loguru
- **Container:** Docker + Docker Compose (local dev)
- **Orchestration:** Kubernetes (production)
- **CI/CD:** GitHub Actions

## Architecture Highlights
- **Multi-tenant design** with Row-Level Security (RLS) in PostgreSQL
- **Async-first** FastAPI backend with connection pooling
- **Webhook receiver** with signature validation
- **Redis queue** for job processing (enhancement:queue)
- **Celery workers** for asynchronous task execution
- **Structured logging** with context propagation
- **Database migrations** via Alembic (auto-applied on Docker startup)

## Project Structure
```
src/
├── api/              # FastAPI endpoints & middleware
├── database/         # SQLAlchemy models & session management
├── cache/            # Redis client & caching utilities
├── services/         # Business logic & service layer
├── workers/          # Celery tasks & configuration
├── enhancement/      # LangGraph workflow & context gatherers
├── monitoring/       # Prometheus metrics instrumentation
├── utils/            # Logging, exceptions, utilities
├── schemas/          # Pydantic validation models
├── config.py         # Configuration management
└── main.py           # FastAPI app entry point

tests/
├── unit/             # Fast, isolated tests
├── integration/      # Multi-component integration tests
└── conftest.py       # Shared pytest fixtures
```

## Development Environment
- **Python Version:** 3.12+ (required)
- **Virtual Environment:** .venv or venv/
- **Package Manager:** pip (via setuptools)
- **Task Runner:** Docker Compose (recommended) or local services
- **Port Mappings:**
  - API: localhost:8000
  - PostgreSQL: localhost:5433 (Docker) or 5432 (local)
  - Redis: localhost:6379
  - Swagger Docs: http://localhost:8000/docs

## Current Status
- **Epic 1:** Foundation & Infrastructure Setup - In Progress
- Recent commits focus on Docker, Kubernetes, Celery, and database setup
- Core infrastructure patterns established, ready for Epic 2 (webhook/enhancement workflow)
