"""
Custom OpenTelemetry Span Processors for Data Redaction and Slow Trace Detection.

This module provides:
- RedactionSpanProcessor: Removes sensitive data from spans before export
- SlowTraceProcessor: Tags spans exceeding 60-second duration for monitoring

Story 4.6: Implement Distributed Tracing with OpenTelemetry
"""

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanProcessor


class RedactionSpanProcessor(SpanProcessor):
    """
    Custom span processor that redacts sensitive attributes before export.

    Protects sensitive data by:
    - Removing attributes containing: api_key, secret, password, token, webhook_secret
    - Truncating long descriptions to prevent data leakage
    - Masking sensitive span attributes with [REDACTED]

    This processor runs on_end, after span completion but before export.
    """

    # Sensitive attribute name patterns to redact
    SENSITIVE_KEYS = {
        "api_key",
        "secret",
        "password",
        "token",
        "webhook_secret",
        "authorization",
        "credential",
    }

    def on_end(self, span: ReadableSpan) -> None:
        """
        Redact sensitive attributes from span before export.

        Args:
            span: The span being exported.
        """
        if not hasattr(span, "attributes") or span.attributes is None:
            return

        # Redact sensitive keys
        attributes_to_remove = []
        for key in span.attributes.keys():
            # Check if key contains any sensitive pattern (case-insensitive)
            if any(
                sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS
            ):
                attributes_to_remove.append(key)

        # Mark sensitive attributes as redacted
        for key in attributes_to_remove:
            span.attributes[key] = "[REDACTED]"

        # Truncate long descriptions to prevent accidental data exposure
        if "ticket.description" in span.attributes:
            desc = span.attributes["ticket.description"]
            if isinstance(desc, str) and len(desc) > 100:
                span.attributes["ticket.description"] = (
                    desc[:100] + "... [TRUNCATED]"
                )

        # Remove webhook payload if present (too large and potentially sensitive)
        if "webhook.payload" in span.attributes:
            span.attributes["webhook.payload"] = "[REDACTED - WEBHOOK PAYLOAD]"

    def shutdown(self) -> None:
        """Shutdown the processor (no-op for redaction processor)."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush any pending operations (no-op for redaction processor).

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if successful.
        """
        return True


class SlowTraceProcessor(SpanProcessor):
    """
    Custom span processor that tags spans exceeding 60-second duration.

    Identifies slow operations for performance monitoring:
    - Tags spans with slow_trace=true if duration > 60 seconds
    - Records actual duration in ms for analysis
    - Enables Jaeger queries: `slow_trace=true`

    Use for identifying performance bottlenecks in ticket enhancement pipeline.
    """

    # Slow trace threshold in seconds
    SLOW_TRACE_THRESHOLD_SECONDS = 60

    def on_end(self, span: ReadableSpan) -> None:
        """
        Tag slow spans with slow_trace attribute.

        Args:
            span: The span being exported.
        """
        if span.start_time is None or span.end_time is None:
            return

        # Calculate duration in milliseconds
        duration_ns = span.end_time - span.start_time
        duration_ms = duration_ns / 1_000_000

        # Tag spans exceeding threshold
        threshold_ms = self.SLOW_TRACE_THRESHOLD_SECONDS * 1000
        if duration_ms > threshold_ms:
            span.attributes["slow_trace"] = True
            span.attributes["duration_ms"] = round(duration_ms, 2)

    def shutdown(self) -> None:
        """Shutdown the processor (no-op for slow trace processor)."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush any pending operations (no-op for slow trace processor).

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if successful.
        """
        return True
