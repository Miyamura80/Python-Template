from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])


@overload
def tool_display(display: str) -> Callable[[F], F]: ...


@overload
def tool_display(display: Callable[[dict[str, Any]], str]) -> Callable[[F], F]: ...


def tool_display(
    display: str | Callable[[dict[str, Any]], str],
) -> Callable[[F], F]:
    """
    Attach an optional human-readable display string (or factory) to a tool function.

    This is intended for UI progress rendering (e.g., in SSE streams) and is separate
    from the tool docstring, which is primarily for LLM tool selection.
    """

    def decorator(func: F) -> F:
        # Stored as a private attribute so wrappers can preserve it via functools.wraps.
        setattr(func, "__tool_display__", display)
        return func

    return decorator
