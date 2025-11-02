# Story 1.3: Set Up PostgreSQL Database with Schema

Status: ready-for-dev

## Story

As a developer,
I want a PostgreSQL database with initial schema for tenant configuration and enhancement history,
So that I can store multi-tenant data with proper isolation.

## Acceptance Criteria

1. PostgreSQL database initialized in Docker container
2. Database migration tool configured (Alembic or similar)
3. Initial schema created with tables: `tenant_configs`, `enhancement_history`
4. Row-level security (RLS) policies defined for tenant isolation
5. Database connection pooling configured in application
6. Database health check endpoint returns 200 OK
7. Sample data can be inserted and queried successfully
8. Migration can be rolled back and re-applied (with automated test)

[Source: docs/epics.md#Story-1.3, docs/tech-spec-epic-1.md#Detailed-Design]

## Tasks / Subtasks

- [ ] **Task 1: Initialize PostgreSQL database and configure Alembic** (AC: #1, #2)
  - [ ] Verify PostgreSQL 17 container running from Story 1.2 docker-compose.yml
  - [ ] Install Alembic dependency in pyproject.toml: `alembic>=1.12.1`
  - [ ] Initialize Alembic in project: `alembic init alembic`
  - [ ] Configure alembic.ini with database URL from environment variable
  - [ ] Update alembic/env.py to use async SQLAlchemy engine
  - [ ] Import Base metadata from src/database/models.py into env.py
  - [ ] Test Alembic connection: `alembic current` should succeed
  - [ ] Create .env variable: AI_AGENTS_DATABASE_URL with PostgreSQL connection string

- [ ] **Task 2: Create database models for tenant_configs table** (AC: #3)
  - [ ] Create src/database/models.py with SQLAlchemy Base
  - [ ] Define TenantConfig model with schema from tech-spec-epic-1.md:
    - [ ] id: UUID primary key (auto-generated)
    - [ ] tenant_id: String(100), unique, not null, indexed
    - [ ] name: String(255), not null
    - [ ] servicedesk_url: String(500), not null
    - [ ] servicedesk_api_key_encrypted: Text, not null
    - [ ] webhook_signing_secret_encrypted: Text, not null
    - [ ] enhancement_preferences: JSON, default={}
    - [ ] created_at: DateTime with timezone, auto-generated (use server_default=func.now())
    - [ ] updated_at: DateTime with timezone, auto-updated (use onupdate=func.now())
  - [ ] Add UUID import from sqlalchemy.dialects.postgresql
  - [ ] Add type hints for all columns

- [ ] **Task 3: Create database model for enhancement_history table** (AC: #3)
  - [ ] Define EnhancementHistory model in src/database/models.py:
    - [ ] id: UUID primary key (auto-generated)
    - [ ] tenant_id: String(100), not null, indexed
    - [ ] ticket_id: String(100), not null, indexed
    - [ ] status: String(50), not null, indexed (values: pending, completed, failed)
    - [ ] context_gathered: JSON (nullable)
    - [ ] llm_output: Text (nullable)
    - [ ] error_message: Text (nullable)
    - [ ] processing_time_ms: Integer (nullable)
    - [ ] created_at: DateTime with timezone, auto-generated (use server_default=func.now())
    - [ ] completed_at: DateTime with timezone (nullable)
  - [ ] Add composite index on (tenant_id, ticket_id) for efficient lookups
  - [ ] Add type hints for all columns

- [ ] **Task 4: Generate and apply initial Alembic migration** (AC: #3, #8)
  - [ ] Generate migration: `alembic revision --autogenerate -m "Initial schema with tenant_configs and enhancement_history"`
  - [ ] Review generated migration file in alembic/versions/
  - [ ] Verify migration includes both tables with all columns
  - [ ] Apply migration: `alembic upgrade head`
  - [ ] Verify tables created in PostgreSQL: `docker-compose exec postgres psql -U aiagents -d ai_agents -c "\dt"`
  - [ ] Test rollback: `alembic downgrade -1`
  - [ ] Re-apply migration: `alembic upgrade head`
  - [ ] Commit migration file to git

- [ ] **Task 5: Implement row-level security policies** (AC: #4)
  - [ ] Create Alembic migration for RLS policies: `alembic revision -m "Add RLS policies for multi-tenant isolation"`
  - [ ] In migration upgrade(), add SQL to enable RLS on enhancement_history table
  - [ ] Create policy: tenant_isolation_policy enforcing tenant_id = current_setting('app.current_tenant_id')
  - [ ] Add SQL to create app_user and admin database roles (per tech spec)
  - [ ] Grant SELECT, INSERT, UPDATE on tenant_configs to app_user
  - [ ] Grant SELECT, INSERT, UPDATE on enhancement_history to app_user
  - [ ] Test migration applies successfully
  - [ ] Document RLS usage in README.md (set session variable before queries)

- [ ] **Task 6: Configure database connection pooling** (AC: #5)
  - [ ] Create src/database/session.py with async SQLAlchemy engine
  - [ ] Use create_async_engine with settings.database_url
  - [ ] Configure pool_size=20 (max connections per tech spec)
  - [ ] Configure pool_pre_ping=True (detect stale connections)
  - [ ] Set pool_timeout=5 (connection timeout per tech spec)
  - [ ] Set echo=True for development environment (log SQL queries)
  - [ ] Create async_session_maker with AsyncSession
  - [ ] Implement get_async_session() dependency for FastAPI
  - [ ] Test connection pool: create session and execute simple query

- [ ] **Task 7: Update health check endpoint to validate database connection** (AC: #6)
  - [ ] Update src/api/health.py to implement database connectivity check
  - [ ] Create check_database_connection() async function in src/database/connection.py or src/api/health.py
  - [ ] Function executes simple query: `SELECT 1` to verify connection
  - [ ] Returns True if query succeeds, False if exception
  - [ ] Update /health/ready endpoint to call check_database_connection()
  - [ ] Test endpoint: `curl http://localhost:8000/health/ready` should show database: connected
  - [ ] Test failure scenario: stop PostgreSQL container and verify health check fails

- [ ] **Task 8: Create sample data insertion and query tests** (AC: #7)
  - [ ] Create tests/integration/test_database.py
  - [ ] Write test_insert_tenant_config() to insert sample tenant
  - [ ] Write test_query_tenant_config() to retrieve tenant by tenant_id
  - [ ] Write test_insert_enhancement_history() to insert sample enhancement record
  - [ ] Write test_query_enhancement_history() to retrieve by tenant_id
  - [ ] Write test_rls_enforcement() to verify tenant isolation (query with different tenant_id returns empty)
  - [ ] **NEW: Write test_migration_rollback_and_reapply()** to verify AC#8 (downgrade and upgrade migrations)
  - [ ] Use pytest-asyncio for async test support
  - [ ] Run tests: `docker-compose exec api pytest tests/integration/test_database.py`
  - [ ] Verify all tests pass

- [ ] **Task 9: Update README.md with database setup instructions** (AC: #1, #8)
  - [ ] Add "Database Setup" section to README.md
  - [ ] Document database initialization on first docker-compose up
  - [ ] Document running migrations: `docker-compose exec api alembic upgrade head`
  - [ ] Document rollback procedure: `alembic downgrade -1`
  - [ ] Document creating new migrations: `alembic revision --autogenerate -m "description"`
  - [ ] Add troubleshooting section: migration conflicts, connection errors
  - [ ] Document environment variable AI_AGENTS_DATABASE_URL format

## Dev Notes

### Architecture Alignment

This story implements the database layer defined in architecture.md and tech-spec-epic-1.md:

**Database Technology:**
- PostgreSQL 17 (per ADR-007) with official postgres:17-alpine Docker image
- SQLAlchemy 2.0+ async ORM for database operations
- Alembic for database migrations and version control
- Asyncpg driver for async PostgreSQL connectivity

**Multi-Tenant Architecture:**
- Row-level security (RLS) policies enforce tenant_id filtering at database level
- Application sets `app.current_tenant_id` session variable before queries
- Database roles: app_user (limited), admin (full access)
- All tenant data tables include tenant_id column with index

**Connection Pooling:**
- Pool size: 5 min, 20 max connections per service (per tech spec)
- Pool pre-ping enabled to detect stale connections
- Pool timeout: 5 seconds (per tech spec)
- Connection timeout: 30 seconds
- Async connection pool for FastAPI async endpoints

**Schema Design:**
- tenant_configs: Stores per-tenant configuration (ServiceDesk credentials, preferences)
- enhancement_history: Audit trail of all enhancement operations
- UUID primary keys for all tables (globally unique, no sequence conflicts)
- Timestamps with timezone for all temporal data (UTC standard)
- JSON/JSONB columns for flexible schema (enhancement_preferences, context_gathered)

### Project Structure Notes

**New Files Created:**
- `alembic.ini` - Alembic configuration file
- `alembic/env.py` - Alembic environment configuration with async support
- `alembic/versions/*.py` - Database migration files
- `src/database/models.py` - SQLAlchemy ORM models
- `src/database/session.py` - Async database session management with pool configuration
- `tests/integration/test_database.py` - Database integration tests (including migration rollback test)

**Modified Files:**
- `pyproject.toml` - Add alembic>=1.12.1 dependency
- `.env.example` - Add AI_AGENTS_DATABASE_URL example
- `src/api/health.py` - Enhanced health check with database connectivity validation
- `src/config.py` - Add database_pool_size and database_pool_timeout configuration
- `README.md` - Database setup and migration documentation

**Directory Structure:**
- `alembic/` - Alembic migrations root
- `alembic/versions/` - Generated migration scripts
- `src/database/` - Database-related modules

### Learnings from Previous Story

**From Story 1.2 (Status: done)**

**Services and Patterns to Reuse:**
- **Configuration Module** (`src/config.py`): Settings class with AI_AGENTS_DATABASE_URL field ready - use for SQLAlchemy engine configuration
- **Docker Compose Stack**: PostgreSQL 17 container already running on port 5433→5432 with health checks
- **Environment Variables**: .env file pattern established - add database-specific variables
- **Health Check Pattern** (`src/api/health.py`): Health endpoint with dependency validation - extend for database checks

**Files to Reference:**
- `docker-compose.yml` - PostgreSQL service configuration (database name, user, password)
- `.env.example` - Update with database connection string template
- `src/config.py` - Use Settings.database_url for SQLAlchemy engine
- `src/api/health.py` - Extend check_database_connection() function
- `src/database/connection.py` - Database health check function exists from Story 1.2

**Architectural Continuity:**
- PostgreSQL 17-alpine - Already running from docker-compose.yml
- Port 5433 (host) → 5432 (container) - Use in connection string
- Database name: ai_agents (from POSTGRES_DB environment variable)
- User credentials: From POSTGRES_USER/POSTGRES_PASSWORD environment variables
- AI_AGENTS_ prefix - Continue for all environment variables

**Technical Patterns Established:**
- Async/await for all I/O operations (FastAPI, database)
- Pydantic Settings for type-safe configuration loading
- Health checks with dependency validation
- Docker volume persistence for data (./data/postgres)
- Integration tests in tests/integration/

**Files Created in Previous Story to Integrate With:**
- `src/database/connection.py` - Database connection module with health check function
- `src/api/health.py` - Health endpoints with PostgreSQL and Redis checks
- `docker-compose.yml` - PostgreSQL service with volume mount and health check
- `.env.example` - Template with database connection strings

**Technical Decisions from Story 1.2:**
- Port 5433 used for host mapping to avoid conflicts with local PostgreSQL installations
- Health checks validate actual connectivity (not just HTTP 200)
- Database connection module separated from main app for reusability

**Review Findings to Address from Story 1.2:**
- **Advisory Note:** Duplicate /health endpoints exist - consolidate in future refactoring. For this story, extend the existing health router implementation in src/api/health.py rather than creating duplicate code.

### Database Schema Details

**tenant_configs Table:**
- Primary purpose: Store multi-tenant configuration
- Encryption: API keys and secrets stored encrypted (encryption implementation in Epic 3)
- Indexing: tenant_id indexed for fast lookups
- JSON preferences: Flexible schema for tenant-specific settings (e.g., {"llm_model": "gpt-4o-mini", "max_context_length": 500})

**enhancement_history Table:**
- Primary purpose: Audit trail and debugging
- Status values: "pending" (queued), "completed" (success), "failed" (error)
- Performance tracking: processing_time_ms for latency monitoring
- Context storage: context_gathered JSON stores results from all context gatherers
- Retention: 90 days (per NFR005, implement in Epic 4)

**Row-Level Security Implementation:**
- Session variable: `app.current_tenant_id` set by middleware per request
- Policy: `USING (tenant_id = current_setting('app.current_tenant_id')::VARCHAR)`
- Enforcement: Automatic tenant_id filtering on all SELECT, INSERT, UPDATE, DELETE
- Testing: Integration tests verify cross-tenant queries return empty results

### Alembic Migration Workflow

**Initial Setup:**
1. `alembic init alembic` - Create alembic directory structure
2. Configure alembic.ini with `sqlalchemy.url` from environment
3. Update alembic/env.py to import models and use async engine
4. Set `target_metadata = Base.metadata` in env.py

**Creating Migrations:**
1. Modify SQLAlchemy models in src/database/models.py
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in alembic/versions/
4. Test migration: `alembic upgrade head`
5. Test rollback: `alembic downgrade -1`
6. Commit migration file to version control

**Migration Best Practices:**
- Always review auto-generated migrations before applying
- Test migrations on development database before production
- Include both upgrade() and downgrade() functions
- Document complex migrations with comments
- Never edit applied migrations (create new migration to fix errors)
- **NEW: Add CI test to validate downgrade/upgrade cycle** (per AC#8 requirement)

### Testing Strategy

**Unit Tests (Minimal):**
- Test SQLAlchemy model instantiation
- Test model validation (e.g., tenant_id required)

**Integration Tests (Primary):**
- Test database connection via async session
- Test tenant_configs CRUD operations
- Test enhancement_history CRUD operations
- Test RLS policy enforcement (cross-tenant query isolation)
- **NEW: Test migration rollback and re-apply (AC#8)** - Verify downgrade and upgrade cycle works
- Test health check endpoint database validation
- Run in Docker environment with real PostgreSQL instance

**Migration Tests:**
- Apply migration on empty database
- Insert sample data
- Rollback migration
- Verify data deleted
- Re-apply migration
- Verify schema recreated

**Manual Validation:**
- Connect to PostgreSQL container and inspect tables
- Verify indexes created: `\d+ tenant_configs`
- Verify RLS enabled: `SELECT relrowsecurity FROM pg_class WHERE relname = 'enhancement_history';`
- Test sample queries with different tenant_id values

### Dependencies Rationale

**Alembic:**
- Industry standard for SQLAlchemy migrations
- Auto-generation from model changes saves time
- Rollback support for safe schema changes
- Version control tracks database schema evolution
- Async support added in Alembic 1.12+

**Asyncpg:**
- Fastest async PostgreSQL driver for Python
- Required by SQLAlchemy async engine
- Connection pooling built-in
- Type-safe query results

**SQLAlchemy 2.0+:**
- Mature, comprehensive ORM
- Async/await support for FastAPI integration
- Relationship management (future epics)
- Query builder prevents SQL injection
- Migration tool ecosystem (Alembic)

### Constraints and Considerations

1. **Migration Order:** All developers must apply migrations in sequence to avoid schema drift
   - Use `alembic upgrade head` to apply all pending migrations
   - Never skip migrations or apply them out of order

2. **RLS Performance:** Row-level security adds query overhead (~5-10%)
   - Acceptable tradeoff for security guarantee
   - Mitigated by tenant_id indexes

3. **Connection Pool Sizing:** 20 max connections per service
   - With 2 API pods + 4 worker pods = 120 total connections
   - PostgreSQL default max_connections = 100 (increase to 200 in production)
   - Document in deployment.md

4. **Async Engine Requirement:** All database operations must use async/await
   - Synchronous SQLAlchemy queries will block event loop
   - Use `await session.execute()` not `session.execute()`

5. **Migration Testing:** Always test migrations on staging before production
   - Create backup before applying production migrations
   - Have rollback plan ready
   - **NEW: Add automated CI test for migration rollback/re-apply cycle** (AC#8)

6. **UUID Storage:** UUIDs use 16 bytes vs 4 bytes for integers
   - Tradeoff: Storage overhead for global uniqueness and security
   - Acceptable for tenant and enhancement record volumes

7. **Server-Side Timestamps:** Use `server_default=func.now()` for timestamp columns
   - Ensures consistency across timezones
   - Prevents client clock skew issues
   - Recommended for future implementation

8. **Pool Timeout Configuration:** Set `pool_timeout=5` seconds as per tech spec
   - Prevents hanging connections
   - Should be configured in src/database/session.py

### Future Extensibility

**Epic 2 Preparation:**
- ticket_history table will be added for context gathering
- system_inventory table for IP address lookups
- Additional indexes on ticket_history.description for full-text search

**Epic 3 Preparation:**
- Encryption functions for servicedesk_api_key_encrypted field
- Additional RLS policies for ticket_history and system_inventory
- Database role management for multi-tenant isolation

**Epic 4 Preparation:**
- Retention policies for enhancement_history (90-day cleanup job)
- Database metrics export for Prometheus monitoring
- Query performance monitoring and slow query logging

### References

- [Source: docs/architecture.md#Data-Architecture]
- [Source: docs/architecture.md#Technology-Stack-Details]
- [Source: docs/tech-spec-epic-1.md#Data-Models-and-Contracts]
- [Source: docs/tech-spec-epic-1.md#APIs-and-Interfaces]
- [Source: docs/epics.md#Story-1.3]
- [Source: stories/1-2-create-docker-configuration-for-local-development.md#Dev-Agent-Record]

## Change Log

- 2025-11-01: Story created (Ravi, SM Agent)
- 2025-11-01: Story updated with review feedback addressed (Ravi, SM Agent)
  - Added automated test requirement for migration rollback/re-apply (AC#8)
  - Clarified Task 7 implementation approach (use check_database_connection helper)
  - Added note about server-side timestamp defaults for future implementation
  - Added pool_timeout=5 configuration to Task 6
  - Enhanced testing strategy section with migration downgrade/upgrade test

## Dev Agent Record

### Context Reference

- Story Context XML: `docs/stories/1-3-set-up-postgresql-database-with-schema.context.xml`
  - Verified: 2025-11-01
  - Status: Ready for development
  - Coverage: Complete (documentation, code refs, interfaces, constraints, test ideas)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
