from __future__ import annotations

import uuid
import time
from datetime import datetime, timezone
from typing import Any, Callable

from dspy.utils.callback import BaseCallback
from loguru import logger as log


def _utc_now_iso() -> str:
    # Match schema example: 2025-12-20T12:34:56.123Z
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _looks_like_secret_key(key: str) -> bool:
    lowered = key.lower()
    secret_substrings = ("key", "token", "secret", "authorization", "cookie")
    return any(part in lowered for part in secret_substrings)


def _truncate_str(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max(0, max_len - 3)] + "..."


def sanitize_tool_payload(
    value: Any,
    *,
    max_depth: int = 4,
    max_items: int = 50,
    max_str_len: int = 2048,
) -> Any:
    """
    Sanitize tool args/results for SSE:
    - redact secret-looking keys
    - truncate long strings
    - bound recursion depth and collection size
    - ensure JSON-serializable output (best-effort)
    """
    if max_depth <= 0:
        return "<truncated>"

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return _truncate_str(value, max_str_len)

    if isinstance(value, bytes):
        return f"<bytes len={len(value)}>"

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= max_items:
                out["<truncated>"] = f"+{len(value) - max_items} more items"
                break
            key_str = str(k)
            if _looks_like_secret_key(key_str):
                out[key_str] = "[REDACTED]"
                continue
            out[key_str] = sanitize_tool_payload(
                v,
                max_depth=max_depth - 1,
                max_items=max_items,
                max_str_len=max_str_len,
            )
        return out

    if isinstance(value, (list, tuple, set)):
        seq = list(value)
        trimmed = seq[:max_items]
        out_list = [
            sanitize_tool_payload(
                item,
                max_depth=max_depth - 1,
                max_items=max_items,
                max_str_len=max_str_len,
            )
            for item in trimmed
        ]
        if len(seq) > max_items:
            out_list.append(f"<truncated +{len(seq) - max_items} items>")
        return out_list

    # Pydantic v2
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump(mode="json")
            return sanitize_tool_payload(
                dumped,
                max_depth=max_depth - 1,
                max_items=max_items,
                max_str_len=max_str_len,
            )
        except Exception:
            pass

    # Fallback to string representation
    try:
        return _truncate_str(str(value), max_str_len)
    except Exception:
        return "<unserializable>"


class ToolStreamingCallback(BaseCallback):
    """
    DSPy callback that emits tool lifecycle events to an external sink.

    Designed to be used alongside Langfuse callbacks (separation of concerns).
    """

    INTERNAL_TOOLS = {"finish", "Finish"}

    def __init__(self, emit: Callable[[dict[str, Any]], None]) -> None:
        super().__init__()
        self._emit = emit
        self._tool_calls: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _tool_name(instance: Any) -> str:
        return (
            getattr(instance, "__name__", None)
            or getattr(instance, "name", None)
            or str(type(instance).__name__)
        )

    @staticmethod
    def _tool_display(instance: Any, sanitized_args: dict[str, Any]) -> str | None:
        display_meta = getattr(instance, "__tool_display__", None)
        if display_meta is None:
            func = getattr(instance, "func", None)  # partial-like
            display_meta = getattr(func, "__tool_display__", None) if func else None

        if isinstance(display_meta, str):
            return display_meta

        if callable(display_meta):
            try:
                rendered = display_meta(sanitized_args)
                return rendered if isinstance(rendered, str) and rendered else None
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

        tool_call_id = call_id or str(uuid.uuid4())

        tool_args = inputs.get("args", {})
        if not tool_args:
            tool_args = {
                k: v for k, v in inputs.items() if k not in ["call_id", "instance"]
            }

        sanitized_args = sanitize_tool_payload(tool_args)
        if not isinstance(sanitized_args, dict):
            sanitized_args = {"value": sanitized_args}

        display = self._tool_display(instance, sanitized_args)
        started_at = time.perf_counter()

        self._tool_calls[tool_call_id] = {
            "tool_name": tool_name,
            "display": display,
            "started_at": started_at,
        }

        event: dict[str, Any] = {
            "type": "tool_start",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "args": sanitized_args,
            "ts": _utc_now_iso(),
        }
        if display:
            event["display"] = display

        self._emit(event)

    def on_tool_end(  # noqa
        self,
        call_id: str,
        outputs: Any | None,
        exception: Exception | None = None,
    ) -> None:
        tool_call_id = call_id
        meta = self._tool_calls.pop(tool_call_id, None)
        if not meta:
            # Likely an internal DSPy tool end event (e.g. Finish) or missing start.
            return

        ended_at = time.perf_counter()
        duration_ms = int(max(0.0, (ended_at - float(meta["started_at"])) * 1000.0))
        tool_name = str(meta.get("tool_name") or "unknown_tool")
        display = meta.get("display")

        if exception is not None:
            event: dict[str, Any] = {
                "type": "tool_error",
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "status": "error",
                "duration_ms": duration_ms,
                "error": {
                    "message": _truncate_str(str(exception), 1024),
                    "kind": type(exception).__name__,
                },
                "ts": _utc_now_iso(),
            }
            if display:
                event["display"] = display
            self._emit(event)
            return

        sanitized_result = sanitize_tool_payload(outputs)
        event = {
            "type": "tool_end",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "status": "success",
            "duration_ms": duration_ms,
            "result": sanitized_result,
            "ts": _utc_now_iso(),
        }
        if display:
            event["display"] = display
        self._emit(event)
