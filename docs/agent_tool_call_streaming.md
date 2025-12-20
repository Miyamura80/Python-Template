## Goal
Extend the existing `/agent/stream` Server-Sent Events (SSE) stream so the frontend can render **real-time tool execution progress** (tool name, args, lifecycle, timing, status) in addition to the existing **token streaming**.

This should work for **any tool** the agent calls (current tool: `alert_admin`, future tools as well), and should be implemented in a way that’s reusable across routes that stream agent output.


## Current behavior (what exists today)

### Streaming route
`src/api/routes/agent/agent.py` implements `/agent/stream` as SSE (`text/event-stream`). It emits JSON events as:

- `start`: includes `user_id`, `conversation_id`, `conversation_title`, `tools_enabled`, `tool_names`
- `token`: incremental text chunks: `{ "type": "token", "content": "..." }`
- `warning`: (e.g. tool streaming fallback)
- `conversation`: final snapshot to persist UI state
- `done` / `error`

### Tool execution visibility
Tool execution is **not** emitted to the client today.

However, DSPy tool executions are already observable in-process:

- `utils/llm/dspy_langfuse.py::LangFuseDSPYCallback` implements `on_tool_start` / `on_tool_end`.
- This is currently used to create Langfuse spans, but it does not forward tool lifecycle events to the SSE client.

### Important limitation in the current streaming architecture
The current SSE generator pulls tokens by doing:

- `async for chunk in inference_module.run_streaming(...)`

If a tool call is synchronous and blocks (common for IO-heavy Python tools), the event loop can be blocked during tool execution. In that case:

- tokens pause (expected)
- heartbeats may not be emitted in time
- **tool_start/tool_end events cannot be flushed “immediately” unless we decouple tool execution from the SSE writer**

This matters because “real-time progress” implies the frontend should receive `tool_start` before the tool finishes.


## Requirements

- **R1: Stream tool calls**: emit start/end/error for each tool invocation.
- **R2: Generic**: applies to any tool callable passed into DSPy ReAct.
- **R3: Backwards compatible**: existing clients/tests expecting `start/token/done` should keep working.
- **R4: Safe payloads**: don’t leak secrets or large blobs; support truncation/redaction.
- **R5: Correlatable**: include a stable `tool_call_id` so UI can group start/end.
- **R6: Works with Langfuse**: keep existing Langfuse tracing; do not break observability.
- **R7: Human-readable progress**: optionally include a UI-friendly `display` string for tool calls, provided by tools via a lightweight decorator.


## Proposed SSE event schema (additive)
All events remain `data: <json>\n\n`.

### Tool lifecycle events

#### `tool_start`
```json
{
  "type": "tool_start",
  "tool_call_id": "<string>",
  "tool_name": "alert_admin",
  "display": "Escalating to an admin for help…",
  "args": { "issue_description": "..." },
  "ts": "2025-12-20T12:34:56.123Z"
}
```

#### `tool_end`
```json
{
  "type": "tool_end",
  "tool_call_id": "<string>",
  "tool_name": "alert_admin",
  "display": "Escalating to an admin for help…",
  "status": "success",
  "duration_ms": 1234,
  "result": { "status": "success", "message": "..." },
  "ts": "2025-12-20T12:34:57.357Z"
}
```

#### `tool_error`
```json
{
  "type": "tool_error",
  "tool_call_id": "<string>",
  "tool_name": "alert_admin",
  "display": "Escalating to an admin for help…",
  "status": "error",
  "duration_ms": 1234,
  "error": {
    "message": "...",
    "kind": "ExceptionType"
  },
  "ts": "2025-12-20T12:34:57.357Z"
}
```

### Notes
- `tool_call_id` should map to DSPy’s callback `call_id` when available; otherwise generate a UUID.
- `args` and `result` must be **sanitized** (see Safety section).
- `display` is optional; when absent, the frontend can fall back to `tool_name` (and/or a mapping).
- Keep existing events unchanged.


## Optional tool decorator for human-readable progress (recommended)
We want tool call events to include a human-friendly string the UI can show (e.g., “Searching GitHub issues…”, “Notifying an admin…”). This should be opt-in per tool, without changing DSPy’s tool discovery (name/docstring) behavior.

### Proposed decorator API
Introduce a decorator that attaches metadata to the tool function:

```python
@tool_display("Escalating to an admin for help…")
def alert_admin(...):
    ...
```

And optionally support dynamic display strings based on arguments:

```python
@tool_display(lambda args: f\"Searching for '{args.get('query', '')}'…\")
def web_search(query: str) -> str:
    ...
```

### Implementation details
- Store metadata on the function object as a private attribute (e.g. `__tool_display__`), so it survives wrapping.
- Ensure `build_tool_wrappers(...)` preserves attributes via `functools.wraps` (it already does).
- In `ToolStreamingCallback`, compute `display` by:
  - checking `getattr(instance, \"__tool_display__\", None)` (string or callable)
  - if callable, call it with the sanitized args dict (and guard with try/except)
  - if missing/invalid, omit `display`

### Why a decorator (vs docstrings)
- Tool docstrings are optimized for LLM tool selection; UI strings are optimized for humans.
- A decorator avoids parsing docstrings and avoids coupling UI to prompt/tool schema.


## Approaches considered (with trade-offs)

### Approach A — Emit tool events from DSPy callback (minimal)
**Idea**: Add a second DSPy callback alongside Langfuse that, on `on_tool_start/on_tool_end`, enqueues `tool_*` events that the SSE generator drains between token chunks.

- **Pros**
  - Minimal code changes; leverages existing DSPy callback mechanism.
  - Generic across all tools with no per-tool edits.
  - Keeps Langfuse callback intact.

- **Cons**
  - If tools block the event loop, the SSE generator can’t flush events until the tool returns.
  - “Real-time” becomes “eventually” for sync/IO-heavy tools.

- **When to choose**
  - Good first step if most tools are fast or async-friendly.


### Approach B — Wrap tools to run out-of-band (executor) while still called by ReAct
**Idea**: Wrap each tool with an adapter that runs the tool in a threadpool and immediately returns control to the loop.

- **Pros**
  - Improves event loop responsiveness.
  - Potentially allows `tool_start` to flush promptly.

- **Cons**
  - DSPy tool calling expectations may be synchronous; returning futures/coroutines may break ReAct.
  - Hard to guarantee compatibility with DSPy internals without deeper validation.

- **When to choose**
  - Only if DSPy supports async tools cleanly in this code path.


### Approach C (recommended) — Move the agent run into a worker thread + event queue
**Idea**: Decouple the SSE writer from the agent execution by running the entire DSPy inference (including tool calls and LLM streaming iteration) in a dedicated worker thread. That worker pushes events into a thread-safe queue; the SSE generator asynchronously drains the queue and sends events immediately.

- **Pros**
  - Best match to “real-time progress” even if tools are blocking/synchronous.
  - Heartbeats become reliable because the SSE writer stays responsive.
  - Generic: works for any tools and any blocking work inside inference.

- **Cons**
  - More complex implementation.
  - Must carefully bridge async/sync streaming (DSPy stream output may be sync or async).
  - Requires thread-safe event emission from callbacks.

- **When to choose**
  - When the product requirement is truly real-time tool visibility.


## Recommended plan
Implement **Approach C** but keep the public route contract **backwards compatible**.

### High-level architecture

- SSE generator is responsible for:
  - emitting `start`
  - emitting events as soon as they arrive from a shared queue
  - emitting heartbeats
  - emitting `done` / `error`

- Worker (thread) is responsible for:
  - creating the DSPy inference module with callbacks
  - iterating the DSPy streaming output
  - pushing `token` events
  - pushing `tool_*` events via a new callback
  - storing enough state for the route to persist the final response (full text)

### Event transport
- Use a **thread-safe queue** for events.
- The SSE generator consumes the queue using `asyncio.to_thread(queue.get)` with a timeout so it can also emit heartbeats.

### Where tool events come from
- Add a new DSPy callback class (e.g. `ToolStreamingCallback`) that implements:
  - `on_tool_start`
  - `on_tool_end`

This callback will:
- ignore internal DSPy tools (`finish`, `Finish`) similar to the Langfuse callback
- sanitize payloads
- push `tool_start/tool_end/tool_error` events into the event queue

### Where token events come from
- The worker iterates the DSPy streaming output and pushes `{type:"token"}` into the event queue.


## Files to change (planned)

### 1) `utils/llm/dspy_inference.py`
- Add optional support for **extra callbacks** in both `run` and `run_streaming`.
  - Today it hardcodes `callbacks=[self.callback]`.
  - Change to `callbacks=[...base_callbacks, ...extra_callbacks]`.

This makes streaming tool events reusable across routes.

### 2) `utils/llm/tool_streaming_callback.py` (new)
- New DSPy callback that emits sanitized `tool_*` events to a provided sink (queue).
- Keep this separate from Langfuse to avoid mixing concerns.

### 2b) `utils/llm/tool_display.py` (new)
- Decorator (e.g. `tool_display(...)`) that attaches an optional human-readable display string (or callable) to a tool function.
- Must be safe to apply to any tool and must not interfere with DSPy tool introspection.

### 3) `src/api/routes/agent/agent.py`
- Update `/agent/stream` implementation to use worker+queue and emit tool lifecycle events.
- Preserve existing events and fields.

### 4) Tests
- Update `tests/e2e/agent/test_agent.py` to tolerate additional event types (it mostly already does).
- Add at least one assertion that tool events are well-formed (may require adding a deterministic test tool, or a feature flag to force a tool call in test mode).


## Payload sanitization / safety

### Redaction rules
Before sending `args`/`result`:
- remove keys that look like secrets: `*key*`, `*token*`, `*secret*`, `authorization`, `cookie` (case-insensitive)
- truncate long strings (e.g. 2–4KB)
- for non-JSON-serializable objects, fall back to `str(obj)` truncated

### Size limits
- cap event payload size to avoid SSE buffering issues and frontend perf problems.

### PII
- do not include `user_id` redundantly in every event; the stream is already user-scoped.


## Open questions / assumptions
(Will be validated during implementation)

- Whether DSPy tool calls execute in the same thread and can block the event loop (assumed yes).
- Whether DSPy’s streaming output is sync or async depending on backend (code already handles both).


## Rollout / compatibility

- Additive event types: existing clients should ignore unknown types.
- Keep `start/token/conversation/done/error` unchanged.
- Optionally gate tool event emission behind a config flag later if needed.


## Concrete step-by-step implementation checklist
1. Introduce `ToolStreamingCallback` that pushes `tool_start/tool_end/tool_error` events to a sink.
2. Extend `DSPYInference` to accept `extra_callbacks` and include them in the `dspy.context(callbacks=...)`.
3. Refactor `/agent/stream` to run inference in a worker thread that emits events into a queue.
4. SSE generator drains the queue, emits heartbeats, and persists the final assistant message as today.
5. Update/extend tests.

