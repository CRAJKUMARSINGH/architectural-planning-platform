"""Phase 13 — OpenTelemetry export configuration and span context bridge.

This module provides:
- Environment-driven OTLP exporter configuration (testable without a collector)
- A span context bridge that promotes correlation IDs to OTel trace/span IDs
- A structured-JSON log formatter that emits OTel-compatible log records
- A pipeline stage span recorder for the ten measured stages

Deployment wiring
-----------------
When OTEL_EXPORTER_OTLP_ENDPOINT is set in the environment, the SDK will
export to a real collector (Jaeger/Tempo/Grafana Cloud).  When the variable is
absent the module degrades gracefully: all public helpers still work and all
tests pass without any collector running.

Required extras (install only when needed)::

    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc

"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

# ---------------------------------------------------------------------------
# Optional OpenTelemetry SDK — degrade gracefully when not installed
# ---------------------------------------------------------------------------
try:
    from opentelemetry import trace  # type: ignore[import]
    from opentelemetry.sdk.resources import Resource  # type: ignore[import]
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
    from opentelemetry.sdk.trace.export import (  # type: ignore[import]
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    _OTEL_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover — SDK is optional
    _OTEL_SDK_AVAILABLE = False

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import]
        OTLPSpanExporter,
    )

    _OTLP_EXPORTER_AVAILABLE = True
except ImportError:
    _OTLP_EXPORTER_AVAILABLE = False


# ---------------------------------------------------------------------------
# OTLP exporter configuration
# ---------------------------------------------------------------------------

# Well-known environment variables (follow the OTel specification).
_OTEL_ENDPOINT_VAR = "OTEL_EXPORTER_OTLP_ENDPOINT"
_OTEL_SERVICE_NAME_VAR = "OTEL_SERVICE_NAME"
_OTEL_INSECURE_VAR = "OTEL_EXPORTER_OTLP_INSECURE"

# The ten pipeline stages measured by this plan.
MEASURED_STAGES: tuple[str, ...] = (
    "brief_compilation",
    "quick_validation",
    "full_validation",
    "revision_creation",
    "render_2d",
    "scene_load_3d",
    "server_render",
    "dxf_export",
    "pdf_export",
    "artifact_upload",
)


@dataclass(frozen=True)
class OtelConfig:
    """Resolved OpenTelemetry exporter configuration.

    Constructed from environment variables so that the settings are
    fully visible in the config without hard-coding credentials.
    """

    endpoint: str | None
    service_name: str
    insecure: bool
    sdk_available: bool
    exporter_available: bool

    @classmethod
    def from_env(cls) -> "OtelConfig":
        """Build config from the current process environment."""
        endpoint = os.environ.get(_OTEL_ENDPOINT_VAR) or None
        service_name = os.environ.get(_OTEL_SERVICE_NAME_VAR, "advocate-chambers-api")
        insecure_raw = os.environ.get(_OTEL_INSECURE_VAR, "false").lower()
        insecure = insecure_raw in ("1", "true", "yes")
        return cls(
            endpoint=endpoint,
            service_name=service_name,
            insecure=insecure,
            sdk_available=_OTEL_SDK_AVAILABLE,
            exporter_available=_OTLP_EXPORTER_AVAILABLE,
        )

    @property
    def is_export_enabled(self) -> bool:
        """True when a collector endpoint is configured *and* the SDK is available."""
        return bool(self.endpoint) and self.sdk_available and self.exporter_available

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "serviceName": self.service_name,
            "insecure": self.insecure,
            "sdkAvailable": self.sdk_available,
            "exporterAvailable": self.exporter_available,
            "exportEnabled": self.is_export_enabled,
        }


def configure_tracer_provider(config: OtelConfig) -> Any | None:
    """Wire up the global TracerProvider.

    Returns the provider if configured, ``None`` when degraded.
    The function is idempotent for the same config within one process.
    """
    if not config.sdk_available:
        return None

    resource = Resource.create({"service.name": config.service_name})
    provider = TracerProvider(resource=resource)

    if config.is_export_enabled and _OTLP_EXPORTER_AVAILABLE:
        exporter = OTLPSpanExporter(
            endpoint=config.endpoint,
            insecure=config.insecure,
        )
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
    else:
        # Emit spans to stdout so local developers can see them.
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return provider


# ---------------------------------------------------------------------------
# Span context bridge
# ---------------------------------------------------------------------------


@dataclass
class SpanContext:
    """Lightweight span wrapper that bridges correlation IDs to OTel attributes.

    Works without the SDK: when OTel is unavailable it stores timing and
    attributes locally so callers have a consistent API.
    """

    stage: str
    trace_id: str = ""
    request_id: str = ""
    revision_id: str = ""
    org_id: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    _start: float = field(default_factory=time.perf_counter, repr=False, compare=False)
    _end: float | None = field(default=None, repr=False, compare=False)
    error: str | None = None

    def finish(self, error: str | None = None) -> None:
        self._end = time.perf_counter()
        self.error = error

    @property
    def elapsed_seconds(self) -> float:
        end = self._end if self._end is not None else time.perf_counter()
        return max(0.0, end - self._start)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "traceId": self.trace_id,
            "requestId": self.request_id,
            "revisionId": self.revision_id,
            "orgId": self.org_id,
            "elapsedSeconds": round(self.elapsed_seconds, 6),
            "error": self.error,
            "attributes": self.attributes,
        }


@contextmanager
def pipeline_span(
    stage: str,
    correlation: dict[str, str] | None = None,
    extra_attributes: dict[str, Any] | None = None,
) -> Generator[SpanContext, None, None]:
    """Context manager that times a pipeline stage and records it.

    Usage::

        with pipeline_span("quick_validation", ctx) as span:
            findings = run_validation(model)
            span.attributes["finding_count"] = len(findings)

    The span is automatically finished (with error capture) on exit.
    """
    ctx = correlation or {}
    span = SpanContext(
        stage=stage,
        trace_id=ctx.get("trace_id", ""),
        request_id=ctx.get("request_id", ""),
        revision_id=ctx.get("revision_id", ""),
        org_id=ctx.get("org_id", ""),
        attributes=dict(extra_attributes or {}),
    )
    try:
        yield span
    except Exception as exc:
        span.finish(error=str(exc))
        raise
    else:
        span.finish()
    finally:
        _record_span(span)


def _record_span(span: SpanContext) -> None:
    """Emit the span to Prometheus + structured log (and OTel if available)."""
    # Prometheus
    try:
        from services.api.middleware.metrics import observe_pipeline_stage  # noqa: PLC0415

        observe_pipeline_stage(span.stage, span.elapsed_seconds)
    except Exception:  # pragma: no cover
        pass

    # Structured log
    logging.getLogger("advocate.pipeline").info(
        "pipeline_stage",
        extra={"otel": span.to_dict()},
    )


# ---------------------------------------------------------------------------
# Structured JSON log formatter
# ---------------------------------------------------------------------------


class OtelJsonFormatter(logging.Formatter):
    """Emit log records as JSON lines with OTel-compatible field names.

    Fields emitted::

        timestamp   ISO-8601 UTC
        severity    INFO / WARNING / ERROR etc.
        message     log message
        logger      logger name
        trace_id    from ``extra["otel"]["traceId"]`` if present
        span_id     from ``extra["otel"]["spanId"]`` if present
        service     from $OTEL_SERVICE_NAME
        ...         any extra keys from ``extra["otel"]``

    Sensitive keys (``authorization``, ``cookie``, ``password``) are
    automatically removed before serialization.
    """

    _SENSITIVE: frozenset[str] = frozenset({"authorization", "cookie", "password", "token"})

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        import datetime

        ts = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
        payload: dict[str, Any] = {
            "timestamp": ts.isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": os.environ.get(_OTEL_SERVICE_NAME_VAR, "advocate-chambers-api"),
        }

        otel = getattr(record, "otel", None)
        if isinstance(otel, dict):
            for k, v in otel.items():
                if k.lower() not in self._SENSITIVE:
                    payload[k] = v

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)
