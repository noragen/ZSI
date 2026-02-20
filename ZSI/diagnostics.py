"""Shared diagnostics helpers for contextual error reporting."""

from __future__ import annotations

import traceback
import uuid
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def append_context_to_exception(ex: Exception, context: str) -> None:
    """Append contextual details to an existing exception without changing type."""
    if not context:
        return
    try:
        text = str(ex)
        if context in text:
            return
        if ex.args:
            ex.args = (f"{ex.args[0]} [{context}]",) + ex.args[1:]
        else:
            ex.args = (context,)
    except Exception:
        pass


def element_context(elt: Any) -> tuple[Any, Any]:
    if elt is None:
        return ("?", "?")
    return (getattr(elt, "namespaceURI", None), getattr(elt, "localName", None) or getattr(elt, "nodeName", None))


def type_context(namespace_uri: Any, name: Any) -> tuple[Any, Any]:
    return (namespace_uri, name)


def add_context_on_exception(context_factory: Callable[..., str]):
    """Decorator to append generated context to any raised exception."""

    def deco(fn: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return fn(*args, **kwargs)
            except Exception as ex:
                append_context_to_exception(ex, context_factory(*args, **kwargs))
                raise

        return wrapper

    return deco


def make_request_id() -> str:
    """Return a short correlation id suitable for logs/fault details."""
    return uuid.uuid4().hex[:12]


def summarize_exception(ex: Exception, tb: Any = None, max_frames: int = 2) -> str:
    """Build a compact, single-line exception summary for diagnostics."""
    try:
        name = ex.__class__.__name__
    except Exception:
        name = "Exception"
    message = str(ex) or "<no-message>"
    parts = [f"{name}: {message}"]
    if tb is not None:
        try:
            frames = traceback.extract_tb(tb)
            tail = frames[-max_frames:] if max_frames > 0 else []
            if tail:
                location = " | ".join(
                    f"{frame.filename}:{frame.lineno}:{frame.name}" for frame in tail
                )
                parts.append(f"at {location}")
        except Exception:
            pass
    return " ; ".join(parts)
