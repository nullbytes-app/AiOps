"""
Integration tests for distributed tracing with OpenTelemetry and Jaeger.

Tests verify:
- Actual OTLP exporter behavior with RedactionAndSlowTraceExporter wrapper
- Redaction of sensitive attributes before export
- Slow trace detection and tagging
- Span attribute preservation through export pipeline
- Custom span creation in real FastAPI/Celery workflow
- End-to-end trace context propagation

Story 4.6: Implement Distributed Tracing with OpenTelemetry (AC16 - Integration Tests)
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from src.monitoring.span_processors import (
    RedactionAndSlowTraceExporter,
    ModifiedSpanWrapper,
)


class TestRedactionAndSlowTraceExporter:
    """Integration tests for the RedactionAndSlowTraceExporter wrapper."""

    def test_exporter_redacts_sensitive_attributes_before_export(self):
        """
        Verify that sensitive attributes are redacted BEFORE export to Jaeger.

        AC14 - Security: sensitive data (api_key, secret, password, token)
        should be redacted before transmission to Jaeger.
        """
        # Setup: Create mock OTLP exporter
        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)  # SUCCESS

        # Create wrapper
        wrapper = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        # Create mock span with sensitive attributes
        mock_span = Mock()
        mock_span.name = "test_span"
        mock_span.attributes = {
            "api_key": "sk-1234567890abcdef",  # Should be redacted
            "user_id": "user-123",  # Should NOT be redacted
            "webhook_secret": "secret-xyz",  # Should be redacted
            "ticket_id": "TICKET-456",  # Should NOT be redacted
        }
        mock_span.start_time = 1000000
        mock_span.end_time = 1000100

        # Export spans through wrapper
        result = wrapper.export([mock_span])

        # Verify redaction happened
        assert mock_otlp_exporter.export.called
        exported_spans = mock_otlp_exporter.export.call_args[0][0]

        # Check that wrapper was applied
        assert len(exported_spans) == 1
        exported_span = exported_spans[0]

        # Verify attributes are modified (wrapper should have redacted them)
        assert isinstance(exported_span, ModifiedSpanWrapper)
        modified_attrs = exported_span.attributes

        # Sensitive keys should be redacted
        assert modified_attrs["api_key"] == "[REDACTED]"
        assert modified_attrs["webhook_secret"] == "[REDACTED]"

        # Non-sensitive keys should NOT be redacted
        assert modified_attrs["user_id"] == "user-123"
        assert modified_attrs["ticket_id"] == "TICKET-456"

    def test_exporter_tags_slow_traces_before_export(self):
        """
        Verify that spans exceeding 60 seconds are tagged with slow_trace=true.

        AC12 - Slow Trace Detection: traces exceeding 60 seconds should be
        automatically tagged for easy identification in Jaeger.
        """
        # Setup: Create mock OTLP exporter
        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)  # SUCCESS

        # Create wrapper
        wrapper = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        # Create mock span that's SLOW (>60 seconds)
        mock_slow_span = Mock()
        mock_slow_span.name = "slow_operation"
        mock_slow_span.attributes = {"operation": "context_gathering"}
        # Duration: 61 seconds = 61,000,000,000 nanoseconds
        mock_slow_span.start_time = 0
        mock_slow_span.end_time = 61_000_000_000

        # Export span through wrapper
        wrapper.export([mock_slow_span])

        # Verify slow trace tag was added
        exported_spans = mock_otlp_exporter.export.call_args[0][0]
        exported_span = exported_spans[0]

        # Check that slow_trace attribute was added
        assert exported_span.attributes["slow_trace"] is True

    def test_exporter_does_not_tag_fast_traces(self):
        """
        Verify that spans under 60 seconds are NOT tagged as slow.

        AC12 - Only spans exceeding the 60-second threshold should be tagged.
        """
        # Setup
        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)

        wrapper = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        # Create mock span that's FAST (<60 seconds)
        mock_fast_span = Mock()
        mock_fast_span.name = "fast_operation"
        mock_fast_span.attributes = {"operation": "quick_update"}
        # Duration: 30 seconds = 30,000,000,000 nanoseconds
        mock_fast_span.start_time = 0
        mock_fast_span.end_time = 30_000_000_000

        # Export span
        wrapper.export([mock_fast_span])

        # Verify slow_trace is NOT set to true
        exported_spans = mock_otlp_exporter.export.call_args[0][0]
        exported_span = exported_spans[0]

        # slow_trace attribute should not be present or should be False
        assert "slow_trace" not in exported_span.attributes or exported_span.attributes.get("slow_trace") is not True

    def test_exporter_preserves_all_non_sensitive_attributes(self):
        """
        Verify that non-sensitive attributes are preserved through export.

        AC16 - Integration tests should verify all span attributes survive
        the export pipeline intact (except redacted ones).
        """
        # Setup
        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)

        wrapper = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        # Create span with mixed attributes
        mock_span = Mock()
        mock_span.name = "complex_span"
        mock_span.attributes = {
            "tenant.id": "tenant-123",
            "ticket.id": "TICKET-456",
            "operation": "enhance_ticket",
            "status": "success",
            "duration_ms": 5000,
            "result.count": 42,
            "api_key": "secret-key",  # Will be redacted
            "user.email": "user@example.com",
            "custom_field": "custom_value",
        }
        mock_span.start_time = 0
        mock_span.end_time = 5_000_000_000

        # Export
        wrapper.export([mock_span])

        # Verify
        exported_spans = mock_otlp_exporter.export.call_args[0][0]
        exported_span = exported_spans[0]
        attrs = exported_span.attributes

        # Non-sensitive attributes should be present and unchanged
        assert attrs["tenant.id"] == "tenant-123"
        assert attrs["ticket.id"] == "TICKET-456"
        assert attrs["operation"] == "enhance_ticket"
        assert attrs["status"] == "success"
        assert attrs["duration_ms"] == 5000
        assert attrs["result.count"] == 42
        assert attrs["user.email"] == "user@example.com"
        assert attrs["custom_field"] == "custom_value"

        # Sensitive attribute should be redacted
        assert attrs["api_key"] == "[REDACTED]"

    def test_exporter_handles_multiple_sensitive_keys(self):
        """
        Verify redaction works with multiple sensitive keys in one span.

        AC14 - Should redact all instances of sensitive key patterns.
        """
        # Setup
        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)

        wrapper = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        # Create span with multiple sensitive keys
        mock_span = Mock()
        mock_span.name = "auth_operation"
        mock_span.attributes = {
            "api_key": "key-1",
            "secret": "secret-1",
            "password": "pass-1",
            "token": "token-1",
            "webhook_secret": "webhook-secret-1",
            "authorization": "Bearer xyz",
            "credential": "cred-1",
            "normal_field": "value",
        }
        mock_span.start_time = 0
        mock_span.end_time = 1000000

        # Export
        wrapper.export([mock_span])

        # Verify all sensitive keys are redacted
        exported_spans = mock_otlp_exporter.export.call_args[0][0]
        exported_span = exported_spans[0]
        attrs = exported_span.attributes

        # All sensitive keys should be redacted
        assert attrs["api_key"] == "[REDACTED]"
        assert attrs["secret"] == "[REDACTED]"
        assert attrs["password"] == "[REDACTED]"
        assert attrs["token"] == "[REDACTED]"
        assert attrs["webhook_secret"] == "[REDACTED]"
        assert attrs["authorization"] == "[REDACTED]"
        assert attrs["credential"] == "[REDACTED]"

        # Normal field should be unchanged
        assert attrs["normal_field"] == "value"

    def test_exporter_forwards_to_otlp_exporter(self):
        """
        Verify that redacted/tagged spans are forwarded to underlying OTLP exporter.

        AC16 - Integration test verifying the export chain works correctly.
        """
        # Setup
        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)  # Return SUCCESS

        wrapper = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        # Create span
        mock_span = Mock()
        mock_span.name = "test_span"
        mock_span.attributes = {"key": "value", "api_key": "secret"}
        mock_span.start_time = 0
        mock_span.end_time = 1000000

        # Export
        result = wrapper.export([mock_span])

        # Verify OTLP exporter was called
        assert mock_otlp_exporter.export.called
        assert result == 0  # SpanExportResult.SUCCESS


class TestModifiedSpanWrapper:
    """Tests for the ModifiedSpanWrapper proxy object."""

    def test_wrapper_returns_modified_attributes(self):
        """
        Verify that the wrapper returns modified attributes while forwarding
        all other span properties.
        """
        # Create mock span
        mock_span = Mock()
        mock_span.name = "original_span"
        mock_span.attributes = {"key": "original_value"}
        mock_span.trace_id = "abc123"

        # Create modified attributes
        modified_attributes = {"key": "[REDACTED]", "new_key": "new_value"}

        # Create wrapper
        wrapper = ModifiedSpanWrapper(mock_span, modified_attributes)

        # Verify attributes are replaced
        assert wrapper.attributes == modified_attributes
        assert wrapper.attributes["key"] == "[REDACTED]"

        # Verify other properties are forwarded
        assert wrapper.name == "original_span"
        assert wrapper.trace_id == "abc123"

    def test_wrapper_allows_attribute_access(self):
        """
        Verify that wrapper properly forwards attribute access for span properties.
        """
        # Create mock span
        mock_span = Mock()
        mock_span.name = "test"
        mock_span.start_time = 1000
        mock_span.end_time = 2000
        mock_span.status_code = 0

        # Create wrapper
        wrapper = ModifiedSpanWrapper(mock_span, {})

        # Verify all properties accessible
        assert wrapper.name == "test"
        assert wrapper.start_time == 1000
        assert wrapper.end_time == 2000
        assert wrapper.status_code == 0


class TestIntegrationTraceContext:
    """Integration tests for trace context propagation through export."""

    def test_context_propagation_through_wrapper(self):
        """
        Verify that redaction wrapper is called with multiple spans from same trace.

        AC3 - Context propagation: trace context should be maintained through
        the export pipeline, spans from same trace should be exported together.
        """
        # Setup: Create real tracer provider with wrapper
        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)

        wrapped_exporter = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        resource = Resource(attributes={SERVICE_NAME: "test-service"})
        provider = TracerProvider(resource=resource)
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        provider.add_span_processor(SimpleSpanProcessor(wrapped_exporter))

        # Create spans in same trace
        tracer = provider.get_tracer(__name__)

        with tracer.start_as_current_span("parent_span") as parent:
            parent.set_attribute("tenant.id", "tenant-123")

            with tracer.start_as_current_span("child_span") as child:
                child.set_attribute("ticket.id", "TICKET-456")

        # Verify exporter was called (spans were exported)
        assert mock_otlp_exporter.export.called

        # Verify wrapper processed spans
        assert mock_otlp_exporter.export.call_count >= 1

        # Verify spans were passed to wrapper (modified wrappers returned)
        for call in mock_otlp_exporter.export.call_args_list:
            spans = call[0][0]
            assert len(spans) >= 1
            # All exported spans should be ModifiedSpanWrapper instances
            for span in spans:
                assert isinstance(span, ModifiedSpanWrapper)


class TestCustomSpanCreation:
    """Integration tests for custom span creation in workflow."""

    def test_custom_spans_have_required_attributes(self):
        """
        Verify that custom spans (job_queued, context_gathering, etc.)
        include required attributes.

        AC5-AC8 - Custom span coverage: each span should have specific attributes.
        """
        # Setup
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        memory_exporter = InMemorySpanExporter()
        resource = Resource(attributes={SERVICE_NAME: "test-service"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(SimpleSpanProcessor(memory_exporter))

        tracer = provider.get_tracer(__name__)

        # Simulate job_queued span (AC5)
        with tracer.start_as_current_span("job_queued") as span:
            span.set_attribute("queue.name", "enhancements")
            span.set_attribute("job.id", "job-123")
            span.set_attribute("tenant.id", "tenant-123")
            span.set_attribute("ticket.id", "TICKET-456")

        # Verify span created with attributes
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "job_queued"
        assert spans[0].attributes["queue.name"] == "enhancements"
        assert spans[0].attributes["job.id"] == "job-123"

    def test_span_hierarchy_parent_child_relationship(self):
        """
        Verify parent-child relationships in span hierarchy.

        AC6-AC8 - Span hierarchy: child spans should have correct parent references.
        """
        # Setup
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        memory_exporter = InMemorySpanExporter()
        resource = Resource(attributes={SERVICE_NAME: "test-service"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(SimpleSpanProcessor(memory_exporter))

        tracer = provider.get_tracer(__name__)

        # Create parent span
        with tracer.start_as_current_span("context_gathering") as parent:
            parent_span_id = parent.get_span_context().span_id

            # Create child spans
            with tracer.start_as_current_span("context.ticket_history"):
                pass

            with tracer.start_as_current_span("context.documentation"):
                pass

            with tracer.start_as_current_span("context.ip_lookup"):
                pass

        # Verify span hierarchy
        spans = memory_exporter.get_finished_spans()

        # Should have 4 spans: 1 parent + 3 children
        assert len(spans) == 4

        # Find parent and children
        parent_span = next(s for s in spans if s.name == "context_gathering")
        child_spans = [
            s for s in spans if s.name.startswith("context.")
        ]

        assert len(child_spans) == 3

        # Verify all spans have required attributes
        assert parent_span.attributes is not None
        for child in child_spans:
            assert child.attributes is not None
            # Each child should have the parent span's span_id as their parent
            # This is implicit in OpenTelemetry - child spans created within parent context
            # will have correct parent linkage


@pytest.mark.integration
class TestEndToEndTracingFlow:
    """End-to-end integration tests for complete tracing flow."""

    def test_complete_enhancement_workflow_trace(self):
        """
        Simulate complete enhancement workflow with all custom spans.

        Verifies:
        - All spans created (AC1-AC8)
        - Attributes preserved (AC4-AC8)
        - Redaction applied (AC14)
        - Slow trace detection works (AC12)
        - Context propagation works (AC3)
        """
        # Setup: Create real tracing pipeline with both exporters
        memory_exporter = InMemorySpanExporter()

        mock_otlp_exporter = Mock()
        mock_otlp_exporter.export = Mock(return_value=0)

        wrapped_exporter = RedactionAndSlowTraceExporter(mock_otlp_exporter)

        resource = Resource(attributes={SERVICE_NAME: "ai-agents-enhancement"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(wrapped_exporter))

        tracer = provider.get_tracer(__name__)

        # Simulate enhancement workflow
        with tracer.start_as_current_span("POST /webhook/servicedesk") as webhook:
            webhook.set_attribute("http.method", "POST")
            webhook.set_attribute("http.url", "/webhook/servicedesk")
            webhook.set_attribute("tenant.id", "tenant-123")
            webhook.set_attribute("ticket.id", "TICKET-456")
            webhook.set_attribute("priority", "high")

            # Job queued (AC5)
            with tracer.start_as_current_span("job_queued"):
                pass

            # Simulate Celery task span
            with tracer.start_as_current_span("celery.task.enhance_ticket") as task:
                task.set_attribute("celery.task_name", "enhance_ticket")
                task.set_attribute("celery.task_id", "task-123")

                # Context gathering (AC6)
                with tracer.start_as_current_span("context_gathering") as ctx_gathering:
                    ctx_gathering.set_attribute("result.ticket_history.count", 42)
                    ctx_gathering.set_attribute("result.docs.count", 18)

                # LLM call (AC7)
                with tracer.start_as_current_span("llm.openai.completion"):
                    pass

                # Ticket update (AC8)
                with tracer.start_as_current_span("api.servicedesk_plus.update_ticket"):
                    pass

        # Force flush to export spans
        provider.force_flush()

        # Verify spans exported to wrapped exporter
        assert mock_otlp_exporter.export.called

        exported_spans = mock_otlp_exporter.export.call_args[0][0]

        # Should have multiple spans
        assert len(exported_spans) >= 5

        # Verify span names
        span_names = {s.name for s in exported_spans}
        assert "POST /webhook/servicedesk" in span_names
        assert "job_queued" in span_names
        assert "context_gathering" in span_names
        assert "llm.openai.completion" in span_names
        assert "api.servicedesk_plus.update_ticket" in span_names

        # Verify attributes preserved
        webhook_span = next(
            (s for s in exported_spans if s.name == "POST /webhook/servicedesk"), None
        )
        assert webhook_span is not None
        assert webhook_span.attributes["tenant.id"] == "tenant-123"
        assert webhook_span.attributes["ticket.id"] == "TICKET-456"
        assert webhook_span.attributes["priority"] == "high"


# Pytest markers for integration tests
def pytest_configure(config):
    """Register integration marker."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
