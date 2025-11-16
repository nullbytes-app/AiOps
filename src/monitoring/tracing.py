"""
OpenTelemetry Distributed Tracing Configuration and Initialization.

This module provides:
- Tracer provider initialization with OTLP exporter
- Automatic instrumentation of FastAPI and Celery
- Custom span processors for data redaction and slow trace detection
- Configuration via environment variables
- Multi-backend support (Jaeger for dev, Uptrace for production)

Story 4.6: Implement Distributed Tracing with OpenTelemetry
Story 12.8: Uptrace Backend Integration (AC4)
"""

import logging
import os
from typing import Dict, Optional

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

logger = logging.getLogger(__name__)


def init_tracer_provider() -> TracerProvider:
    """
    Initialize and configure the OpenTelemetry tracer provider.

    Creates a TracerProvider with:
    - OTLP gRPC exporter for trace export to Jaeger (dev) or Uptrace (production)
    - BatchSpanProcessor for efficient batch export
    - Custom RedactionSpanProcessor to remove sensitive data
    - Custom SlowTraceProcessor to tag slow traces (>60s)

    Environment variables:
    - OTEL_BACKEND: Backend type, "jaeger" or "uptrace" (default: jaeger)
    - OTEL_EXPORTER_OTLP_ENDPOINT: Collector endpoint (default: http://jaeger:4317)
    - OTEL_SERVICE_NAME: Service name in traces (default: ai-agents-enhancement)
    - OTEL_TRACES_SAMPLER: Sampling strategy (default: traceidratio)
    - OTEL_TRACES_SAMPLER_ARG: Sampling rate 0.0-1.0 (default: 0.1 = 10%)
    - UPTRACE_DSN: Uptrace Data Source Name (required if OTEL_BACKEND=uptrace)

    Story 12.8 AC4: Multi-backend support with seamless switching via OTEL_BACKEND env var.

    Returns:
        TracerProvider: Configured tracer provider instance.
    """
    # Load configuration from environment
    backend = os.getenv("OTEL_BACKEND", "jaeger").lower()
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

    # Story 12.8 AC4: Configure OTLP exporter based on backend
    if backend == "uptrace":
        # Uptrace production backend configuration
        otlp_endpoint = os.getenv("UPTRACE_OTLP_ENDPOINT", "https://uptrace.example.com:4317")
        uptrace_dsn = os.getenv("UPTRACE_DSN")

        if not uptrace_dsn:
            logger.warning(
                "UPTRACE_DSN not set - traces will be exported without authentication. "
                "Set UPTRACE_DSN environment variable for production deployments."
            )
            headers: Dict[str, str] = {}
        else:
            headers = {"uptrace-dsn": uptrace_dsn}

        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, headers=headers)

        logger.info(
            f"OpenTelemetry initialized with Uptrace backend",
            extra={
                "backend": "uptrace",
                "endpoint": otlp_endpoint,
                "service_name": service_name,
                "has_dsn": bool(uptrace_dsn),
            }
        )
    else:
        # Jaeger development backend configuration (Story 4.6 existing)
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)

        logger.info(
            f"OpenTelemetry initialized with Jaeger backend",
            extra={
                "backend": "jaeger",
                "endpoint": otlp_endpoint,
                "service_name": service_name,
            }
        )

    # Wrap OTLP exporter with redaction and slow trace detection
    # This wrapper (Story 4.6 AC12 & AC14 + Story 12.8 AC7):
    # - Redacts sensitive attributes (api_key, secret, password, token, mcp_server_env)
    # - Tags spans exceeding 60 seconds with slow_trace=true
    # - Forwards modified spans to configured backend (Jaeger or Uptrace) via OTLP
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
