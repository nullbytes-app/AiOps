"""
OpenTelemetry Distributed Tracing Configuration and Initialization.

This module provides:
- Tracer provider initialization with OTLP exporter
- Automatic instrumentation of FastAPI and Celery
- Custom span processors for data redaction and slow trace detection
- Configuration via environment variables

Story 4.6: Implement Distributed Tracing with OpenTelemetry
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.monitoring.span_processors import (
    RedactionSpanProcessor,
    SlowTraceProcessor,
    RedactionAndSlowTraceExporter,
)


def init_tracer_provider() -> TracerProvider:
    """
    Initialize and configure the OpenTelemetry tracer provider.

    Creates a TracerProvider with:
    - OTLP gRPC exporter for trace export to Jaeger
    - BatchSpanProcessor for efficient batch export
    - Custom RedactionSpanProcessor to remove sensitive data
    - Custom SlowTraceProcessor to tag slow traces (>60s)

    Environment variables:
    - OTEL_EXPORTER_OTLP_ENDPOINT: Jaeger collector endpoint (default: http://jaeger:4317)
    - OTEL_SERVICE_NAME: Service name in traces (default: ai-agents-enhancement)
    - OTEL_TRACES_SAMPLER: Sampling strategy (default: traceidratio)
    - OTEL_TRACES_SAMPLER_ARG: Sampling rate 0.0-1.0 (default: 0.1 = 10%)

    Returns:
        TracerProvider: Configured tracer provider instance.
    """
    # Load configuration from environment
    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"
    )
    service_name = os.getenv("OTEL_SERVICE_NAME", "ai-agents-enhancement")

    # Create resource with service metadata
    resource = Resource(
        attributes={
            SERVICE_NAME: service_name,
            "service.version": "0.1.0",
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development"),
        }
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Configure OTLP exporter for Jaeger
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)

    # Wrap OTLP exporter with redaction and slow trace detection
    # This wrapper (AC12 & AC14):
    # - Redacts sensitive attributes (api_key, secret, password, token)
    # - Tags spans exceeding 60 seconds with slow_trace=true
    # - Forwards modified spans to Jaeger via OTLP
    wrapped_exporter = RedactionAndSlowTraceExporter(otlp_exporter)

    # Configure batch span processor for performance optimization
    # BatchSpanProcessor batches spans before export, reducing overhead
    batch_processor = BatchSpanProcessor(
        wrapped_exporter,
        max_queue_size=2048,  # Buffer up to 2048 spans before blocking
        schedule_delay_millis=5000,  # Export every 5 seconds
        max_export_batch_size=512,  # Send max 512 spans per export
        export_timeout_millis=30000,  # Timeout after 30s
    )
    tracer_provider.add_span_processor(batch_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)

    return tracer_provider


def get_tracer(name: str, version: Optional[str] = None) -> trace.Tracer:
    """
    Get a named tracer instance from the global tracer provider.

    Args:
        name: Tracer name, typically the module name (__name__)
        version: Optional version string for the tracer

    Returns:
        Tracer: Named tracer instance for creating spans.

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my_operation") as span:
            span.set_attribute("key", "value")
    """
    return trace.get_tracer(name, version)
