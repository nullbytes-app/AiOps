# Row-Level Security (RLS) Implementation

**Story:** 3.1 - Implement Row-Level Security in PostgreSQL
**Status:** Implemented (2025-11-02)
**Acceptance Criteria:** 1-7

## Overview

Row-Level Security (RLS) provides database-level multi-tenant data isolation using PostgreSQL's native security policies. This ensures that even if application-level filtering fails, tenant data remains isolated at the database layer.

## Architecture

### Session Variable Pattern

RLS policies filter rows based on the session variable `app.current_tenant_id`:

```sql
USING (tenant_id = current_setting('app.current_tenant_id')::VARCHAR)
```

### Helper Function

The `set_tenant_context(tenant_id VARCHAR)` function:
- Validates tenant_id exists in tenant_configs
- Sets the session variable securely
- Uses SECURITY DEFINER to prevent privilege escalation

### Protected Tables

RLS is enabled on:
- `tenant_configs`
- `enhancement_history`
- `ticket_history`
- `system_inventory`

## Application Integration

### FastAPI Endpoints

Use the `get_tenant_db` dependency for RLS-aware sessions:

```python
from src.api.dependencies import get_tenant_db

@app.post("/enhancements")
async def create_enhancement(
    data: EnhancementCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    # All queries automatically filtered by tenant_id
    enhancement = EnhancementHistory(**data.dict())
    db.add(enhancement)
    await db.commit()
```

### Celery Tasks

Set tenant context at the start of each task:

```python
from src.database.tenant_context import set_db_tenant_context

async with async_session_maker() as session:
    await set_db_tenant_context(session, job.tenant_id)
    # All subsequent queries filtered by tenant_id
```

## Security Considerations

### Bypassing RLS

- **Superusers** and roles with `BYPASSRLS` attribute bypass all RLS policies
- **Database admin role** should have BYPASSRLS for maintenance
- **Application role** (`app_user`) should NOT have BYPASSRLS

### SQL Injection Protection

- The `set_tenant_context()` function validates tenant_id exists before setting
- Always use parameterized queries: `session.execute(text(sql), {"tenant_id": tenant_id})`
- NEVER concatenate tenant_id directly into SQL strings

### Missing Tenant Context

If tenant context is not set:
- Queries return **0 rows** (safe default)
- No error is raised
- This prevents accidental data exposure

## Troubleshooting

### Empty Result Sets

**Symptom:** Queries return no rows unexpectedly

**Causes:**
1. Tenant context not set before query
2. Incorrect tenant_id in context
3. Querying as wrong tenant

**Solution:**
```python
# Check current tenant context
result = await session.execute(
    text("SELECT current_setting('app.current_tenant_id', true)")
)
print(f"Current tenant: {result.scalar()}")
```

### Permission Denied Errors

**Symptom:** `permission denied for table X`

**Causes:**
1. Using admin role instead of app_user role
2. RLS enabled but no policies created
3. Missing GRANT permissions

**Solution:**
- Verify connection uses `app_user` role, not admin
- Check policies exist: `SELECT * FROM pg_policies WHERE tablename = 'table_name';`

### Invalid Tenant ID

**Symptom:** `Invalid tenant_id: X` exception

**Cause:** Tenant doesn't exist in tenant_configs table

**Solution:**
- Verify tenant exists: `SELECT tenant_id FROM tenant_configs;`
- Create tenant configuration before setting context

## Performance

### Overhead

RLS adds minimal overhead (<5%) with simple policy expressions like:
```sql
tenant_id = current_setting('app.current_tenant_id')::VARCHAR
```

### Optimization

- Ensure `tenant_id` columns are indexed on all RLS tables
- Keep policy expressions simple (avoid subqueries)
- Use EXPLAIN ANALYZE to verify query plans

## Testing

### Unit Tests

`tests/unit/test_row_level_security.py` validates:
- Tenant context management
- Cross-tenant isolation (SELECT, UPDATE, DELETE)
- Missing context behavior
- Policy structure

### Manual Testing

```sql
-- Set context
SELECT set_tenant_context('tenant-a');

-- Verify filtering
SELECT * FROM enhancement_history;  -- Only tenant-a rows

-- Switch context
SELECT set_tenant_context('tenant-b');
SELECT * FROM enhancement_history;  -- Only tenant-b rows
```

## Migration

The RLS implementation is deployed via Alembic migration:
```bash
python -m alembic upgrade head
```

To rollback:
```bash
python -m alembic downgrade -1
```

## References

- PostgreSQL Documentation: [Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- Story Context: `docs/stories/3-1-implement-row-level-security-in-postgresql.context.xml`
- Migration: `alembic/versions/168c9b67e6ca_add_row_level_security_policies.py`
- PRD FR018: Multi-tenant data isolation requirements
