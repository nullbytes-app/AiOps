# Runbook: Login Issues

**Objective:** Diagnose and resolve user authentication failures in the Next.js UI

**Severity:** High (blocks user access to platform)

**Estimated Time:** 5-15 minutes

---

## Prerequisites

Before starting, ensure you have:
- [ ] User's email address
- [ ] Access to application logs (`docker logs nextjs-ui` or `kubectl logs`)
- [ ] Access to Redis (for token blacklist checks)
- [ ] Access to PostgreSQL (for user table queries)
- [ ] FastAPI `/api/v1/auth/login` endpoint accessible

---

## Decision Tree

```
User cannot log in
├── Wrong Password (Most Common)
│   ├── Error: "Invalid email or password"
│   ├── Solution: Reset password via "Forgot password?" link
│   └── Prevention: User education on password policy
│
├── Account Locked
│   ├── Error: "Account locked. Try again in X minutes"
│   ├── Cause: 5+ failed login attempts within 15 minutes
│   ├── Solution: Wait 15 minutes OR admin manually unlock
│   └── Check: `users.failed_login_attempts`, `users.locked_until`
│
├── Expired Token (After Login)
│   ├── Error: "Token expired. Please log in again"
│   ├── Cause: Access token expired (7 days), refresh token expired (30 days)
│   ├── Solution: Re-login via `/auth/login`
│   └── Prevention: Use refresh token before expiration
│
├── Invalid/Revoked Token
│   ├── Error: "Invalid token" or "Token revoked"
│   ├── Cause: Token in Redis blacklist (after logout)
│   ├── Solution: Clear browser cache, re-login
│   └── Check: Redis key `revoked:{token_hash}`
│
└── Other Issues
    ├── Network/CORS errors
    ├── Backend API down
    └── Database connection issues
```

---

## Step-by-Step Troubleshooting

### Issue 1: Wrong Password

**Symptoms:**
- Error message: "Invalid email or password"
- User is certain they entered correct password

**Diagnosis:**
1. Check if user account exists:
   ```sql
   SELECT id, email, failed_login_attempts, locked_until
   FROM users
   WHERE email = 'user@example.com';
   ```

2. If no results → User not registered
3. If `failed_login_attempts` < 5 → Password is incorrect

**Solution:**
1. **User Self-Service:**
   - Click "Forgot password?" on login page
   - Enter email → Check inbox for reset link
   - Set new password (12+ chars, uppercase, number, special char)

2. **Admin Action (if email not working):**
   ```bash
   # Generate password reset token manually
   python scripts/create_password_reset_token.py user@example.com
   # Copy token and share securely with user
   ```

**Verification:**
- User can log in with new password
- `failed_login_attempts` resets to 0 on successful login

---

### Issue 2: Account Locked

**Symptoms:**
- Error message: "Account locked. Try again in 15 minutes."
- User cannot log in even with correct password

**Diagnosis:**
1. Check lock status:
   ```sql
   SELECT email, failed_login_attempts, locked_until
   FROM users
   WHERE email = 'user@example.com';
   ```

2. If `failed_login_attempts` >= 5 AND `locked_until` > NOW() → Account locked

**Solution:**

**Option A: Wait for Auto-Unlock (15 minutes)**
- Lock expires automatically after 15 minutes
- No admin action needed

**Option B: Manual Admin Unlock**
```sql
UPDATE users
SET failed_login_attempts = 0,
    locked_until = NULL
WHERE email = 'user@example.com';
```

**Verification:**
```sql
SELECT email, failed_login_attempts, locked_until
FROM users
WHERE email = 'user@example.com';
-- Expect: failed_login_attempts = 0, locked_until = NULL
```

**Prevention:**
- Enable MFA (future enhancement)
- Monitor `auth_audit_log` for repeated lock-outs (may indicate brute force attack)

---

### Issue 3: Expired Token (After Successful Login)

**Symptoms:**
- User logged in successfully, but after navigating gets "Token expired"
- Happens after 7 days (access token expiration) or 30 days (refresh token expiration)

**Diagnosis:**
1. Check browser console:
   ```javascript
   // Error in Network tab:
   // GET /api/v1/agents -> 401 Unauthorized
   // Response: { "detail": "Token expired" }
   ```

2. Check token in browser DevTools → Application → Local Storage → `nextjs-ui` → `next-auth.session-token`

**Solution:**
1. **Auto-Refresh (if refresh token valid):**
   - NextAuth auto-refreshes access token if refresh token valid (< 30 days)
   - No user action needed

2. **Manual Re-Login (if refresh token expired):**
   - User clicks "Log in again" button
   - Redirects to `/auth/login`
   - Enter credentials → New tokens issued

**Verification:**
- User can access protected pages (e.g., `/dashboard`)
- No 401 errors in Network tab

**Configuration:**
```bash
# .env
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days (default)
REFRESH_TOKEN_EXPIRE_MINUTES=43200  # 30 days (default)
```

---

### Issue 4: Invalid or Revoked Token

**Symptoms:**
- Error: "Invalid token" or "Token revoked"
- Happens after explicit logout, even if user didn't log out manually

**Diagnosis:**
1. Check if token in blacklist:
   ```bash
   # Redis CLI
   redis-cli
   > KEYS revoked:*
   > GET revoked:{token_hash}
   # If key exists → Token revoked
   ```

2. Check browser console for 401 errors

**Solution:**
1. **Clear Browser Cache:**
   ```
   Chrome: Cmd+Shift+Delete (Ctrl+Shift+Delete) → Clear cookies and site data
   Firefox: Cmd+Shift+Delete → Cookies and Site Data
   Safari: Cmd+Option+E → Empty Caches
   ```

2. **Re-Login:**
   - Navigate to `/auth/login`
   - Enter credentials
   - New token issued (not in blacklist)

**Verification:**
- User can access `/dashboard` without errors
- New token not in Redis blacklist

---

### Issue 5: Network or CORS Errors

**Symptoms:**
- Error in browser console: "CORS policy: No 'Access-Control-Allow-Origin' header"
- Error: "Network request failed"

**Diagnosis:**
1. Check browser console → Network tab
   ```
   POST /api/v1/auth/login -> Failed
   Status: (failed) net::ERR_CONNECTION_REFUSED
   OR
   Status: 403 Forbidden (CORS error)
   ```

2. Check FastAPI logs:
   ```bash
   docker logs ai-agents-api
   # Look for CORS errors or connection refused
   ```

**Solution:**

**A. FastAPI Not Running:**
```bash
# Check if API container running
docker ps | grep ai-agents-api

# If not running, start it
docker-compose up -d ai-agents-api

# Verify health
curl http://localhost:8000/health
# Expect: {"status": "healthy"}
```

**B. CORS Misconfigured:**
```python
# src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

Restart FastAPI after config change.

**Verification:**
- `/api/v1/health` returns 200 OK
- Login request succeeds (200 OK with JWT token in response)

---

### Issue 6: Database Connection Issues

**Symptoms:**
- Error: "Database connection failed"
- Login hangs indefinitely

**Diagnosis:**
1. Check PostgreSQL connectivity:
   ```bash
   # From FastAPI container
   docker exec -it ai-agents-api sh
   python -c "from src.database.session import check_database_connection; check_database_connection()"
   ```

2. Check logs for DB errors:
   ```bash
   docker logs ai-agents-api | grep -i "database"
   ```

**Solution:**
```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check connection from API
docker-compose logs api | grep "Database connected"

# Verify database URL in .env
cat .env | grep DATABASE_URL
# Expect: postgresql+asyncpg://user:password@postgres:5432/ai_agents
```

**Verification:**
```bash
curl http://localhost:8000/health/ready
# Expect: {"status": "ready", "dependencies": {"database": "connected", "redis": "connected"}}
```

---

## Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Invalid email or password" | Wrong password OR user doesn't exist | Reset password OR check if user registered |
| "Account locked. Try again in X minutes" | 5+ failed login attempts | Wait 15 min OR admin unlock |
| "Token expired. Please log in again" | Access token expired (7 days) | Re-login to get new token |
| "Invalid token" | Token revoked (after logout) | Clear cache, re-login |
| "CORS policy error" | Frontend-backend CORS mismatch | Check `allow_origins` in FastAPI |
| "Network request failed" | API not running | Start FastAPI container |
| "Database connection failed" | PostgreSQL down | Restart postgres container |

---

## Diagnostic Commands

```bash
# Check user account status
docker exec -it ai-agents-postgres psql -U aiagents -d ai_agents -c \
  "SELECT email, failed_login_attempts, locked_until FROM users WHERE email = 'user@example.com';"

# Check recent login attempts (last 10)
docker exec -it ai-agents-postgres psql -U aiagents -d ai_agents -c \
  "SELECT event_type, success, ip_address, created_at FROM auth_audit_log ORDER BY created_at DESC LIMIT 10;"

# Check Redis blacklist
docker exec -it ai-agents-redis redis-cli KEYS "revoked:*"

# Check API health
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# Check Next.js logs
docker logs nextjs-ui --tail 50

# Check FastAPI logs
docker logs ai-agents-api --tail 50
```

---

## Escalation

If issue persists after following this runbook:

1. **Collect Diagnostic Info:**
   - User email
   - Error screenshot
   - Browser console output (Network tab + Console tab)
   - FastAPI logs (`docker logs ai-agents-api --tail 100`)
   - Database query results (user status, audit logs)

2. **Contact:**
   - **Level 2 Support:** Slack #ai-agents-support
   - **On-Call Engineer:** PagerDuty escalation

3. **Temporary Workaround:**
   - Create new user account for affected user
   - Grant same roles as original account
   - Investigate original account issue asynchronously

---

**Last Updated:** January 2025
**Version:** 1.0
**Owner:** Operations Team
