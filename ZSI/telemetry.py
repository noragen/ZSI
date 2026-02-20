"""Optional telemetry hooks for parse/serialize/resolve/generator paths.

This module is intentionally dependency-optional:
- If OpenTelemetry is installed, spans are emitted.
- If not installed, all hooks are no-ops.
"""

from __future__ import annotations

from contextlib import contextmanager
import time
from typing import Any

from ZSI.wstools.logging import getLogger as _GetLogger

_log = _GetLogger("ZSI.telemetry")


def _otel_tracer():
    try:
        from opentelemetry import trace  # type: ignore
    except Exception:
        return None
    return trace.get_tracer("ZSI")


@contextmanager
def span(name: str, **attrs: Any):
    """Create an optional telemetry span and log a debug event."""
    tracer = _otel_tracer()
    start = time.perf_counter()
    if tracer is None:
        _log.debug("span start", event="telemetry.span.start", span=name)
        try:
            yield None
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            _log.debug(
                "span end",
                event="telemetry.span.end",
                span=name,
                duration_ms=round(duration_ms, 3),
            )
        return

    with tracer.start_as_current_span(name) as otel_span:
        for key, value in attrs.items():
            if value is None:
                continue
            try:
                otel_span.set_attribute(key, value)
            except Exception:
                continue
        try:
            yield otel_span
        except Exception as ex:
            try:
                otel_span.record_exception(ex)
            except Exception:
                pass
            raise
