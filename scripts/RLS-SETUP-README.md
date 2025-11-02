# RLS Setup Completion Guide

**Story:** 3.1 - Implement Row-Level Security in PostgreSQL
**Status:** Code fixes complete, awaiting database setup

---

## ✅ Code Fixes Already Applied

The following fixes have been completed by Amelia (Senior Developer Review):

1. **Fixed test file syntax error** ✓
   - File: `tests/unit/test_row_level_security.py:64`
   - Fixed class name split issue

2. **Updated webhook endpoint** ✓
   - File: `src/api/webhooks.py:38-54`
   - Added RLS-aware database session dependency

---

## 🚀 Quick Start (Automated)

Run the complete setup script:

```bash
cd /Users/ravi/Documents/nullBytes_Apps/Ai_Agents/AI\ Ops

# Start Docker Desktop first (if not running)

# Then run the setup script:
./scripts/complete-rls-setup.sh
```

The script will:
- ✓ Check Docker status
- ✓ Start PostgreSQL and Redis
- ✓ Apply RLS migration
- ✓ Verify RLS policies
- ✓ Run RLS tests
- ✓ Run full test suite
- ✓ Generate summary report

**Expected Time:** 5-10 minutes

---

## 📋 Manual Steps (If Preferred)

If you prefer to run steps manually:

### Step 1: Start Docker
```bash
# Start Docker Desktop application (macOS)
# Or start Docker daemon on Linux
```

### Step 2: Start Database Services
```bash
cd /Users/ravi/Documents/nullBytes_Apps/Ai_Agents/AI\ Ops
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 5

# Verify services are running
docker ps | grep -E "postgres|redis"
```

### Step 3: Apply RLS Migration
```bash
# Run Alembic migration
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade ... -> 168c9b67e6ca, add_row_level_security_policies
```

### Step 4: Verify RLS Policies
```bash
# Check RLS is enabled on tables
docker exec -it $(docker ps -qf "name=postgres") psql -U postgres -d ai_agents -c "
SELECT
    tablename,
    relrowsecurity as rls_enabled
FROM pg_tables t
JOIN pg_class c ON c.relname = t.tablename
WHERE schemaname = 'public'
    AND tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory');
"

# Check policies exist
docker exec -it $(docker ps -qf "name=postgres") psql -U postgres -d ai_agents -c "
SELECT
    tablename,
    policyname,
    cmd
FROM pg_policies
WHERE policyname LIKE '%tenant_isolation%';
"

# Expected: 4 policies, all with cmd = '*' (FOR ALL)
```

### Step 5: Run RLS Tests
```bash
# Run RLS-specific tests
pytest tests/unit/test_row_level_security.py -v

# Expected: 12 tests collected, all should pass
```

### Step 6: Run Full Test Suite
```bash
# Run all tests
pytest tests/ -v

# Review any failures (many should now be fixed with database running)
```

---

## 🔍 Verification Checklist

After running the setup, verify:

- [ ] Docker is running
- [ ] PostgreSQL container is up
- [ ] Migration applied successfully
- [ ] RLS enabled on 4 tables (tenant_configs, enhancement_history, ticket_history, system_inventory)
- [ ] 4 RLS policies created (all tables have tenant_isolation_policy)
- [ ] 12 RLS unit tests passing
- [ ] Database integration tests now passing (previously failed due to no database)

---

## 📊 Expected Test Results

**Before fixes:**
- Test file: Syntax error (couldn't import)
- RLS tests: 0 collected (syntax error)
- Database tests: 49 failures (Docker not running)

**After fixes + database running:**
- Test file: Imports successfully ✓
- RLS tests: 12 collected, 12 passing ✓
- Database tests: Should mostly pass ✓

---

## ⚠️ Troubleshooting

### Issue: "Docker daemon not running"
**Solution:** Start Docker Desktop app or Docker daemon

### Issue: "Migration already applied"
**Solution:** This is fine - migration is idempotent. Check RLS status in Step 4.

### Issue: "Connection refused to PostgreSQL"
**Solution:**
```bash
# Check if container is running
docker ps | grep postgres

# Check container logs
docker logs $(docker ps -qf "name=postgres")

# Restart if needed
docker-compose restart postgres
```

### Issue: "Some tests still failing"
**Solution:**
1. Check which tests are failing
2. If RLS tests pass but others fail, those may be pre-existing issues
3. Focus on verifying RLS functionality first

---

## 📝 Next Steps After Success

Once all RLS tests pass:

1. **Re-run code review workflow**
   ```bash
   /bmad:bmm:workflows:code-review
   ```

2. **Mark story as ready** (if review passes)

3. **Update sprint status** (story moves from "review" to "done")

4. **Commit changes:**
   ```bash
   git add tests/unit/test_row_level_security.py src/api/webhooks.py
   git commit -m "Fix RLS implementation blockers

   - Fix test file syntax error (line 64)
   - Update webhook endpoint to use RLS-aware dependency
   - Story 3.1 now ready for re-review"
   ```

---

## 📚 Related Documentation

- **Story File:** `docs/stories/3-1-implement-row-level-security-in-postgresql.md`
- **Review Report:** See "Senior Developer Review (AI)" section in story file
- **RLS Documentation:** `docs/security-rls.md`
- **Migration File:** `alembic/versions/168c9b67e6ca_add_row_level_security_policies.py`

---

## 🎯 Success Criteria

Story 3.1 is unblocked when:
- [x] Test syntax error fixed
- [x] Webhook endpoint uses RLS dependency
- [ ] Database running
- [ ] Migration applied
- [ ] All 12 RLS tests passing
- [ ] No critical blockers in code review

**Current Status:** 2/6 complete (awaiting database setup)

---

**Questions?** Refer to the comprehensive review in the story file or re-run code-review workflow after completing setup.
