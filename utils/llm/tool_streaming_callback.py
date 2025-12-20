from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Literal

from dspy.utils.callback import BaseCallback
from loguru import logger as log


def _utc_now_iso() -> str:
    # Use a stable UTC ISO string with Z suffix for frontend friendliness.
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|key|token|secret|authorization|cookie|password)",
    re.IGNORECASE,
)


def _sanitize_for_json(
    value: Any,
    *,
    max_depth: int = 4,
    max_str_len: int = 4096,
    max_list_len: int = 50,
) -> Any:
    if max_depth <= 0:
        return "[TRUNCATED]"

    if value is None:
        return None

    if isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        if len(value) > max_str_len:
            return value[:max_str_len] + "…"
        return value

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            key_str = str(k)
            if _SECRET_KEY_RE.search(key_str):
                sanitized[key_str] = "[REDACTED]"
                continue
            sanitized[key_str] = _sanitize_for_json(
                v,
                max_depth=max_depth - 1,
                max_str_len=max_str_len,
                max_list_len=max_list_len,
            )
        return sanitized

    if isinstance(value, (list, tuple, set)):
        items = list(value)[:max_list_len]
        return [
            _sanitize_for_json(
                item,
                max_depth=max_depth - 1,
                max_str_len=max_str_len,
                max_list_len=max_list_len,
            )
            for item in items
        ]

    # Pydantic v2 models
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _sanitize_for_json(
                model_dump(mode="json"),
                max_depth=max_depth - 1,
                max_str_len=max_str_len,
                max_list_len=max_list_len,
            )
        except Exception:
            pass

    # Best-effort object dict
    if hasattr(value, "__dict__"):
        try:
            return _sanitize_for_json(
                dict(value.__dict__),
                max_depth=max_depth - 1,
                max_str_len=max_str_len,
                max_list_len=max_list_len,
            )
        except Exception:
            pass

    # Last resort
    try:
        return _sanitize_for_json(
            str(value),
            max_depth=max_depth - 1,
            max_str_len=max_str_len,
            max_list_len=max_list_len,
        )
    except Exception:
        return "[UNSERIALIZABLE]"


class ToolStreamingCallback(BaseCallback):
    """
    DSPy callback that emits tool lifecycle events to a provided sink.

    This is intended to power real-time UI updates (e.g. SSE streams) and is
    separate from the Langfuse callback, which is for observability.
    """

    INTERNAL_TOOLS = {"finish", "Finish"}

    def __init__(
        self,
        event_sink: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__()
        self._event_sink = event_sink
        self._start_times: dict[str, float] = {}
        self._tool_names: dict[str, str] = {}
        self._tool_displays: dict[str, str] = {}

    def _tool_name(self, instance: Any) -> str:
        return (
            getattr(instance, "__name__", None)
            or getattr(instance, "name", None)
            or str(type(instance).__name__)
        )

    def _tool_display(self, instance: Any, args: dict[str, Any]) -> str | None:
        display = getattr(instance, "__tool_display__", None)
        if display is None:
            return None
        if isinstance(display, str):
            return display
        if callable(display):
            try:
                computed = display(args)
                if isinstance(computed, str) and computed:
                    return computed
            except Exception as e:
                log.debug(f"tool_display callable failed: {e}")
                return None
        return None

    def on_tool_start(  # noqa
        self,
        call_id: str,
        instance: Any,
        inputs: dict[str, Any],
    ) -> None:
        tool_name = self._tool_name(instance)
        if tool_name in self.INTERNAL_TOOLS:
            return

        tool_args = inputs.get("args", {})
        if not tool_args:
            tool_args = {
                k: v for k, v in inputs.items() if k not in ["call_id", "instance"]
            }

        sanitized_args = _sanitize_for_json(tool_args)
        display = self._tool_display(
            instance, sanitized_args if isinstance(sanitized_args, dict) else {}
        )

        self._start_times[call_id] = time.perf_counter()
        self._tool_names[call_id] = tool_name
        if display:
            self._tool_displays[call_id] = display

        payload: dict[str, Any] = {
            "type": "tool_start",
            "tool_call_id": call_id,
            "tool_name": tool_name,
            "args": sanitized_args,
            "ts": _utc_now_iso(),
        }
        if display:
            payload["display"] = display

        self._event_sink(payload)

    def on_tool_end(  # noqa
        self,
        call_id: str,
        outputs: Any | None,
        exception: Exception | None = None,
    ) -> None:
        tool_name = self._tool_names.get(call_id, "unknown_tool")
        if tool_name in self.INTERNAL_TOOLS:
            return

        start = self._start_times.pop(call_id, None)
        duration_ms = int((time.perf_counter() - start) * 1000) if start else None

        status: Literal["success", "error"] = "success"
        event_type = "tool_end"
        payload: dict[str, Any] = {
            "tool_call_id": call_id,
            "tool_name": tool_name,
            "ts": _utc_now_iso(),
        }
        display = self._tool_displays.pop(call_id, None)
        if display:
            payload["display"] = display
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms

        if exception is not None:
            status = "error"
            event_type = "tool_error"
            payload["status"] = status
            payload["error"] = {
                "message": str(exception),
                "kind": type(exception).__name__,
            }
        else:
            payload["status"] = status
            payload["result"] = _sanitize_for_json(outputs)

        payload["type"] = event_type
        self._event_sink(payload)
