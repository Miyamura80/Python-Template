from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])


@overload
def tool_display(display: str) -> Callable[[F], F]: ...


@overload
def tool_display(display: Callable[[dict[str, Any]], str]) -> Callable[[F], F]: ...


def tool_display(display: str | Callable[[dict[str, Any]], str]) -> Callable[[F], F]:
    """
    Attach a UI-friendly display string (or callable) to a tool function.

    This is intentionally separate from docstrings (LLM-facing) so the frontend
    can render human-readable tool progress without changing tool discovery.
    """

    def decorator(func: F) -> F:
        setattr(func, "__tool_display__", display)
        return func

    return decorator
