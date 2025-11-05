# Plugin Error Handling Guide

[Plugin Docs](index.md) > How-To Guides > Error Handling

**Last Updated:** 2025-11-05

---

## Overview

Comprehensive error handling patterns for plugin development, including exception hierarchy, retry strategies, and graceful degradation.

---

## Exception Hierarchy

**Location:** `src/plugins/exceptions.py`

```python
class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


class ValidationError(PluginError):
    """Raised when payload validation fails."""
    pass


class APIError(PluginError):
    """Raised when external API call fails."""

    def __init__(self, message: str, retry_count: int = 0, last_error: Exception = None):
        super().__init__(message)
        self.retry_count = retry_count
        self.last_error = last_error


class AuthenticationError(PluginError):
    """Raised when API authentication fails (401/403)."""
    pass


class RateLimitError(PluginError):
    """Raised when API rate limit exceeded (429)."""

    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class ConfigurationError(PluginError):
    """Raised when tenant configuration is invalid or missing."""
    pass
```

---

## Error Handling Patterns

### Pattern 1: Retry with Exponential Backoff

**Use Case:** Transient network errors, API server errors (5xx)

```python
async def get_ticket_with_retry(
    self,
    tenant_id: str,
    ticket_id: str,
    max_attempts: int = 3
) -> Optional[Dict[str, Any]]:
    """Get ticket with exponential backoff retry."""

    last_error = None
    for attempt in range(max_attempts):
        try:
            return await self._get_ticket_single_attempt(tenant_id, ticket_id)

        except httpx.HTTPStatusError as e:
            last_error = e

            # Don't retry authentication errors
            if e.response.status_code in (401, 403):
                raise AuthenticationError(f"Invalid credentials: {e}")

            # Handle rate limiting
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 2 ** attempt))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                continue

            # Exponential backoff for other errors
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)

        except httpx.RequestError as e:
            last_error = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)

    # All attempts failed
    raise APIError(
        f"Failed to get ticket after {max_attempts} attempts",
        retry_count=max_attempts,
        last_error=last_error
    )
```

**Backoff Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 1s (2^0)
- Attempt 3: Wait 2s (2^1)
- Attempt 4: Wait 4s (2^2)

### Pattern 2: Graceful Degradation

**Use Case:** Non-critical operations that shouldn't block workflow

```python
async def update_ticket_with_fallback(
    self,
    tenant_id: str,
    ticket_id: str,
    content: str
) -> bool:
    """Update ticket with graceful degradation."""

    try:
        return await self.update_ticket(tenant_id, ticket_id, content)

    except AuthenticationError as e:
        # Log error, alert ops team, but don't crash workflow
        logger.error(f"Authentication error updating ticket {ticket_id}: {e}")
        await send_alert("Plugin authentication failure", str(e))
        return False

    except APIError as e:
        # Log error, queue for retry, continue workflow
        logger.error(f"API error updating ticket {ticket_id}: {e}")
        await queue_retry_task(tenant_id, ticket_id, content)
        return False

    except Exception as e:
        # Unexpected error - log and continue
        logger.exception(f"Unexpected error updating ticket {ticket_id}: {e}")
        return False
```

### Pattern 3: Validation with Context

**Use Case:** Webhook payload validation with detailed error messages

```python
def extract_metadata_with_validation(
    self,
    payload: Dict[str, Any]
) -> TicketMetadata:
    """Extract metadata with detailed validation errors."""

    try:
        # Validate required top-level fields
        if "data" not in payload:
            raise ValidationError("Missing 'data' field in payload")

        if "ticket" not in payload["data"]:
            raise ValidationError("Missing 'data.ticket' field in payload")

        ticket_data = payload["data"]["ticket"]

        # Validate required ticket fields
        required_fields = ["id", "description", "priority", "created_time"]
        missing_fields = [f for f in required_fields if f not in ticket_data]
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Extract and validate types
        try:
            ticket_id = str(ticket_data["id"])
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid ticket ID format: {e}")

        try:
            created_at = datetime.fromtimestamp(
                int(ticket_data["created_time"]) / 1000,
                tz=timezone.utc
            )
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid timestamp format: {e}")

        return TicketMetadata(...)

    except KeyError as e:
        raise ValidationError(f"Missing required field: {e}")

    except ValidationError:
        # Re-raise validation errors with original context
        raise

    except Exception as e:
        # Catch unexpected errors and wrap in ValidationError
        raise ValidationError(f"Unexpected error extracting metadata: {e}")
```

### Pattern 4: Circuit Breaker

**Use Case:** Prevent cascade failures when external service is down

```python
class CircuitBreaker:
    """Circuit breaker for external API calls."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""

        # Circuit is open - reject immediately
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
            else:
                raise APIError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)

            # Success - reset failure count
            if self.state == "half-open":
                self.state = "closed"
                logger.info("Circuit breaker closed")
            self.failure_count = 0
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error("Circuit breaker opened")

            raise
```

---

## Error Handling by Method

### validate_webhook()

**Errors to Handle:**
- Missing tenant_id → Log error, return False
- Tenant not found → Log error, return False
- Decryption failure → Log error, return False
- Signature mismatch → Log warning, return False
- Unexpected errors → Log exception, return False

```python
async def validate_webhook(...) -> bool:
    try:
        # Validation logic
        return True
    except Exception as e:
        logger.error(f"Webhook validation error: {e}")
        return False  # Never raise, always return bool
```

### get_ticket()

**Errors to Handle:**
- 404 Not Found → Return None
- 401/403 Auth Error → Raise AuthenticationError
- 429 Rate Limit → Wait and retry
- 5xx Server Error → Retry with backoff
- Timeout → Retry with backoff
- Network Error → Retry with backoff

```python
async def get_ticket(...) -> Optional[Dict[str, Any]]:
    for attempt in range(3):
        try:
            response = await client.get(url)

            if response.status_code == 404:
                return None  # Not found

            if response.status_code in (401, 403):
                raise AuthenticationError("Invalid credentials")

            if response.status_code == 429:
                # Retry with rate limit backoff
                continue

            response.raise_for_status()
            return response.json()

        except httpx.RequestError:
            if attempt == 2:
                raise APIError("Network error after 3 attempts")
            await asyncio.sleep(2 ** attempt)
```

### update_ticket()

**Errors to Handle:**
- 401/403 Auth Error → Raise AuthenticationError
- 429 Rate Limit → Wait and retry
- 404 Not Found → Return False
- 5xx Server Error → Retry, then return False
- Timeout → Retry, then return False

```python
async def update_ticket(...) -> bool:
    for attempt in range(3):
        try:
            response = await client.post(url, json=payload)

            if response.status_code in (401, 403):
                raise AuthenticationError("Invalid credentials")

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                await asyncio.sleep(retry_after)
                continue

            if response.status_code == 404:
                logger.warning("Ticket not found")
                return False

            response.raise_for_status()
            return True

        except httpx.RequestError:
            if attempt == 2:
                return False  # Failed after retries
            await asyncio.sleep(2 ** attempt)

    return False
```

### extract_metadata()

**Errors to Handle:**
- Missing required fields → Raise ValidationError with field name
- Invalid data types → Raise ValidationError with details
- Null values → Use defaults or raise ValidationError
- Unexpected payload structure → Raise ValidationError

```python
def extract_metadata(...) -> TicketMetadata:
    try:
        # Extraction logic with validations
        return TicketMetadata(...)

    except KeyError as e:
        raise ValidationError(f"Missing field: {e}")

    except (TypeError, ValueError) as e:
        raise ValidationError(f"Invalid data type: {e}")
```

---

## Logging Best Practices

### Log Levels

```python
# DEBUG: Detailed diagnostic info
logger.debug(f"Attempting ticket retrieval: {ticket_id}")

# INFO: Important events
logger.info(f"Ticket {ticket_id} retrieved successfully")

# WARNING: Something unexpected but recoverable
logger.warning(f"Rate limited, retrying after {retry_after}s")

# ERROR: Error that affects functionality
logger.error(f"Authentication error: {e}")

# CRITICAL: System-level failures
logger.critical(f"Database connection lost")
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "ticket_retrieved",
    ticket_id=ticket_id,
    tenant_id=tenant_id,
    duration_ms=duration,
    attempt=attempt
)
```

### Don't Log Secrets

```python
# ✅ GOOD: Mask credentials
logger.info(f"Using API key: {api_key[:4]}***")

# ❌ BAD: Expose full credential
logger.info(f"Using API key: {api_key}")
```

---

## Testing Error Handling

### Unit Test: Retry Logic

```python
@pytest.mark.asyncio
async def test_get_ticket_retries_on_500():
    """Test retry logic for 500 server error."""
    plugin = ServiceDeskPlusPlugin()

    mock_response = Mock()
    mock_response.status_code = 500

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            await plugin.get_ticket("tenant-001", "123")

        assert "3 attempts" in str(exc_info.value)
        assert mock_client.call_count == 3  # Verify retry
```

### Unit Test: Authentication Error

```python
@pytest.mark.asyncio
async def test_get_ticket_raises_on_401():
    """Test authentication error raised immediately (no retry)."""
    plugin = ServiceDeskPlusPlugin()

    mock_response = Mock()
    mock_response.status_code = 401

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        with pytest.raises(AuthenticationError):
            await plugin.get_ticket("tenant-001", "123")

        assert mock_client.call_count == 1  # No retry on auth error
```

---

## See Also

- [Plugin Interface Reference](plugin-interface-reference.md)
- [Plugin Performance Guide](plugin-performance.md)
- [Plugin Testing Guide](plugin-testing-guide.md)
