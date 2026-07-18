"""Optional Langfuse tracing.

Tracing is enabled only when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
are set. Without them, decorators become no-ops and the API still works.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def is_langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def observe(
    func: F | None = None,
    *,
    name: str | None = None,
    as_type: str | None = None,
    capture_input: bool | None = None,
    capture_output: bool | None = None,
) -> F | Callable[[F], F]:
    """Langfuse @observe wrapper that no-ops when credentials are missing."""

    def decorator(fn: F) -> F:
        if not is_langfuse_enabled():
            return fn

        from langfuse import observe as langfuse_observe

        kwargs: dict[str, Any] = {}
        if name is not None:
            kwargs["name"] = name
        if as_type is not None:
            kwargs["as_type"] = as_type
        if capture_input is not None:
            kwargs["capture_input"] = capture_input
        if capture_output is not None:
            kwargs["capture_output"] = capture_output

        return langfuse_observe(**kwargs)(fn)

    if func is not None:
        return decorator(func)
    return decorator


def update_generation(**kwargs: Any) -> None:
    if not is_langfuse_enabled():
        return

    try:
        from langfuse import get_client

        get_client().update_current_generation(**kwargs)
    except Exception:
        # Tracing must never break the research request.
        return


def update_span(**kwargs: Any) -> None:
    if not is_langfuse_enabled():
        return

    try:
        from langfuse import get_client

        get_client().update_current_span(**kwargs)
    except Exception:
        return


def flush_langfuse() -> None:
    if not is_langfuse_enabled():
        return

    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        return


def with_trace_metadata(**metadata: Any) -> Callable[[F], F]:
    """Attach metadata to the current span when tracing is enabled."""

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            update_span(metadata=metadata)
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
