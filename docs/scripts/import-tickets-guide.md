# ServiceDesk Plus Bulk Import Script Guide

**Purpose**: Bulk import historical tickets from ServiceDesk Plus API during tenant onboarding to seed the enhancement agent with context data.

**Location**: `scripts/import_tickets.py`

## Quick Start

### Basic Usage

```bash
python scripts/import_tickets.py --tenant-id=acme-corp
```

This imports the last 90 days of closed/resolved tickets for the `acme-corp` tenant.

### Advanced Usage

**Import specific date range:**
```bash
python scripts/import_tickets.py --tenant-id=acme-corp \
  --start-date=2024-01-01 \
  --end-date=2024-03-31
```

**Import 6 months of history:**
```bash
python scripts/import_tickets.py --tenant-id=acme-corp --days=180
```

**Enable debug logging:**
```bash
python scripts/import_tickets.py --tenant-id=acme-corp --log-level=DEBUG
```

## Prerequisites

Before running the import script, ensure:

1. **Tenant Configuration Entry**: The tenant must exist in the `tenant_configs` table with:
   - `tenant_id`: Unique identifier for the tenant
   - `base_url`: ServiceDesk Plus API base URL (e.g., `https://sdp.manageengine.com`)
   - `api_key`: Zoho OAuth token for authentication

2. **Database Connection**: PostgreSQL database must be running and accessible via connection string in `.env` or `src/config.py`

3. **Dependencies Installed**:
   ```bash
   pip install httpx loguru sqlalchemy asyncpg
   ```

4. **API Credentials**: Valid ServiceDesk Plus API key with permission to read request/ticket data

## Command-Line Options

### Required

- `--tenant-id` (required): Tenant identifier to import tickets for
  - Example: `--tenant-id=acme-corp`

### Date Range (choose one)

- `--days` (default: 90): Number of days of history to import
  - Example: `--days=180` (import 6 months)
  - Default: 90 days

OR

- `--start-date` (optional, ISO format): Import from this date (YYYY-MM-DD)
  - Example: `--start-date=2024-01-01`

- `--end-date` (optional, ISO format): Import until this date (YYYY-MM-DD)
  - Example: `--end-date=2024-03-31`
  - Default: Today's date

### Logging

- `--log-level` (optional, default: INFO): Set logging verbosity
  - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`
  - Example: `--log-level=DEBUG`

## Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | Import completed without errors |
| 1 | Invalid Arguments | Missing `--tenant-id` or invalid date format |
| 2 | Tenant Not Found | `--tenant-id` not in `tenant_configs` table |
| 3 | API Error | Authentication failed, server error, all retries exhausted |

### Example Error Handling (Bash)

```bash
python scripts/import_tickets.py --tenant-id=acme-corp
EXIT_CODE=$?

case $EXIT_CODE in
  0) echo "Import successful" ;;
  1) echo "Invalid arguments - check tenant ID and date format" ;;
  2) echo "Tenant not found - configure in tenant_configs table first" ;;
  3) echo "API error - check credentials and ServiceDesk Plus API availability" ;;
  *) echo "Unknown error (code $EXIT_CODE)" ;;
esac
```

## Script Behavior

### Import Process

1. **Load Configuration**: Fetch tenant's ServiceDesk Plus credentials from `tenant_configs` table
2. **Calculate Date Range**: Determine start/end dates based on `--days`, `--start-date`, `--end-date`
3. **Pagination Loop**:
   - Fetch up to 100 tickets per API request
   - Extract and transform ticket data
   - Insert into `ticket_history` table
   - Handle duplicates via `UNIQUE(tenant_id, ticket_id)` constraint
4. **Progress Tracking**: Log "Imported X/Y tickets (Z%)" every 100 tickets
5. **Rate Limiting**: 0.6s delay between API requests (respects 100 req/min limit)
6. **Final Summary**: Log total imported, skipped, and elapsed time

### Data Extraction

Each ticket is transformed as follows:

| ServiceDesk Plus Field | TicketHistory Field | Transformation |
|------------------------|-------------------|---|
| `id` | `ticket_id` | Convert to string |
| `subject` | `description` (part 1) | Combined with description |
| `description` | `description` (part 2) | Combined with subject |
| `resolution.content` | `resolution` | Plain text |
| `resolved_time.value` | `resolved_date` | Convert from milliseconds to datetime |
| `tags[].name` | (included in description) | Comma-separated list |
| *added* | `source` | Set to `"bulk_import"` |
| *added* | `ingested_at` | Timestamp of ingestion |
| *added* | `tenant_id` | From `--tenant-id` argument |

### Error Handling

The script is **resilient to errors**. It will:

- **Skip invalid tickets**: Missing required fields, malformed data
- **Log errors**: Each error is logged with context (tenant_id, ticket_id, error type)
- **Continue processing**: Invalid tickets don't halt the import
- **Retry on transient failures**:
  - Rate limit (429): Wait 60s, retry up to 3 times
  - Server error (500, 502, 503): Exponential backoff, retry up to 3 times
  - Timeout: Retry up to 3 times with exponential backoff
  - **Do NOT retry** on auth errors (401, 403): Exit immediately with code 3

### Idempotency

The import is **idempotent**. You can re-run with the same data safely:

- **UNIQUE constraint**: `UNIQUE(tenant_id, ticket_id)` prevents duplicates
- **Behavior**:
  - First run: 5000 tickets imported, 0 skipped
  - Second run with same data: 0 imported, 5000 skipped (duplicates)
  - Result: Still only 5000 tickets in database, no errors

## Output Examples

### Successful Import

```
2025-11-02 14:23:45 | INFO     | Starting import for tenant 'acme-corp' from ServiceDesk Plus API
2025-11-02 14:23:45 | INFO     | Import date range: 2025-08-04 to 2025-11-02
2025-11-02 14:23:47 | DEBUG    | Fetching page: start_index=1, row_count=100
2025-11-02 14:23:47 | DEBUG    | Fetched 100 tickets, has_more_rows=true
2025-11-02 14:23:48 | INFO     | Imported 100/100 tickets (100%)
2025-11-02 14:23:48 | DEBUG    | Fetching page: start_index=101, row_count=100
2025-11-02 14:23:48 | DEBUG    | Fetched 75 tickets, has_more_rows=false
2025-11-02 14:23:48 | INFO     | Imported 175/175 tickets (100%)
2025-11-02 14:23:48 | INFO     | All pages fetched
2025-11-02 14:23:48 | INFO     | Import complete: 175 imported, 0 skipped, 175 processed in 3.2s
```

### Import with Duplicates

```
2025-11-02 14:25:00 | INFO     | Starting import for tenant 'acme-corp' from ServiceDesk Plus API
2025-11-02 14:25:00 | INFO     | Import date range: 2025-08-04 to 2025-11-02
...
2025-11-02 14:25:02 | INFO     | Imported 100/175 tickets (57%)
2025-11-02 14:25:02 | DEBUG    | Duplicate ticket (tenant_id=acme-corp, ticket_id=5678), skipping
2025-11-02 14:25:02 | DEBUG    | Duplicate ticket (tenant_id=acme-corp, ticket_id=5679), skipping
...
2025-11-02 14:25:05 | INFO     | Import complete: 175 imported, 0 skipped, 175 processed in 5.1s
```

### Error: Tenant Not Found

```
2025-11-02 14:26:00 | ERROR    | Tenant 'unknown-tenant' not found in tenant_configs
```
Exit code: 2

### Error: Authentication Failed

```
2025-11-02 14:27:00 | ERROR    | Authentication error: 401. Exiting.
```
Exit code: 3

## Troubleshooting

### Issue: "Tenant not found in tenant_configs"

**Cause**: The tenant ID doesn't exist in the database.

**Solution**: Create the tenant in `tenant_configs`:
```sql
INSERT INTO tenant_configs (tenant_id, base_url, api_key)
VALUES ('acme-corp', 'https://sdp.manageengine.com', 'zoho-oauth-token-here');
```

### Issue: "Authentication failed (401)"

**Cause**: The API key is invalid or expired.

**Solution**:
1. Generate a new Zoho OAuth token from ServiceDesk Plus
2. Update the `api_key` in `tenant_configs` table
3. Retry the import

### Issue: "Rate limit hit (429)"

**Cause**: ServiceDesk Plus API rate limit (100 requests/minute) exceeded.

**Solution**: Script automatically retries after 60s. It will continue processing.

### Issue: "Server error (500)"

**Cause**: ServiceDesk Plus API server error.

**Solution**: Script automatically retries with exponential backoff. If error persists, wait and try again later.

### Issue: "Timeout"

**Cause**: Network latency or slow API response.

**Solution**: Script automatically retries. Check network connectivity and ServiceDesk Plus API status.

### Issue: Import is slow

**Cause**: Database performance or network latency.

**Solution**:
- Verify database connection pooling is working (check `src/database/session.py`)
- Check ServiceDesk Plus API response times
- Consider importing smaller date ranges at a time
- Enable DEBUG logging to identify bottlenecks

## Integration Points

### Database

- **Table**: `ticket_history`
- **Fields Written**: `tenant_id`, `ticket_id`, `description`, `resolution`, `resolved_date`, `source`, `ingested_at`, `created_at`, `updated_at`
- **Constraints**: `UNIQUE(tenant_id, ticket_id)` for idempotency

### ServiceDesk Plus API

- **Endpoint**: `GET /api/v3/requests`
- **Authentication**: `Authorization: Zoho-oauthtoken {api_key}` header
- **Rate Limit**: 100 requests/minute (0.6s delay between requests)
- **Statuses Fetched**: "Closed" and "Resolved"

### Story Integration

- **Story 2.5A**: This script (bulk import)
- **Story 2.5**: Uses imported data for ticket history search
- **Story 2.5B**: Webhook automatically stores resolved tickets (ongoing ingestion)

## Performance Characteristics

- **Target**: 100 tickets/minute
- **10,000 tickets**: ~100 minutes (1.7 hours)
- **Actual time depends on**:
  - Network latency to ServiceDesk Plus API
  - Database insert performance
  - Number of tickets per page (max 100)
  - Rate limiting delays (0.6s per request)

## Next Steps

After successful import:

1. **Verify Data**:
   ```sql
   SELECT COUNT(*) FROM ticket_history WHERE tenant_id = 'acme-corp';
   SELECT * FROM ticket_history WHERE tenant_id = 'acme-corp' LIMIT 10;
   ```

2. **Run Story 2.5**: Implement ticket history search using the imported data

3. **Test Search**: Query tickets for similarity matching

4. **Monitor**: Check `ingested_at` timestamps to verify import freshness

## Related Documentation

- [ServiceDesk Plus API v3 Documentation](https://www.manageengine.com/products/service-desk/sdpod-v3-api/)
- [Technical Specification - Epic 2](docs/tech-spec-epic-2.md)
- [Story 2.5A - Populate Ticket History](docs/stories/2-5A-populate-ticket-history-from-servicedesk-plus.md)
- [Story 2.5 - Ticket History Search](docs/stories/2-5-implement-ticket-history-search-context-gathering.md)
