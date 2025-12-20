# Tool Call Streaming Design Document

## Overview

This document outlines the design for implementing real-time tool call streaming in the Agent endpoint. The goal is to stream information about tool calls being executed by the Agent so that the frontend can render real-time progress of what the Agent is doing.

## Current Architecture

### Existing Streaming Infrastructure

The current `/agent/stream` endpoint uses Server-Sent Events (SSE) to stream token-by-token responses:

```python
# Current event types emitted:
{
    "type": "start",        # Initial metadata
    "type": "token",        # Individual tokens
    "type": "warning",      # Warnings (e.g., tool fallback)
    "type": "conversation", # Final conversation snapshot
    "type": "done",         # Completion signal
    "type": "error"         # Error messages
}
```

### Tool Infrastructure

- **Tools Location**: `src/api/routes/agent/tools/`
- **Tool Registration**: Via `get_agent_tools()` → `build_tool_wrappers()` 
- **Tool Execution**: DSPY's `ReAct` module handles tool calls
- **Observability**: `LangFuseDSPYCallback` already has `on_tool_start` and `on_tool_end` hooks

### Key Components

```
┌──────────────────────────────────────────────────────────────────┐
│                      /agent/stream endpoint                       │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐    ┌─────────────────┐    ┌───────────────┐ │
│  │  DSPYInference │───▶│ ReAct Module    │───▶│ Tool Wrappers │ │
│  │  (streaming)   │    │ (tool calling)  │    │ (user context)│ │
│  └────────────────┘    └─────────────────┘    └───────────────┘ │
│          │                     │                                  │
│          │              ┌──────┴──────┐                          │
│          │              │ LangFuse    │                          │
│          │              │ Callback    │                          │
│          ▼              │ (on_tool_*) │                          │
│  ┌────────────────┐     └─────────────┘                          │
│  │  SSE Stream    │                                              │
│  │  Generator     │ ──── Currently NO tool events emitted ────▶ │
│  └────────────────┘                                              │
└──────────────────────────────────────────────────────────────────┘
```

## Proposed Tool Call Event Types

```python
# New event types to add:
{
    "type": "tool_start",
    "tool_name": "alert_admin",
    "tool_call_id": "call_abc123",
    "arguments": {"issue_description": "..."},
    "timestamp": "2025-12-20T10:00:00Z"
}

{
    "type": "tool_end",
    "tool_name": "alert_admin",
    "tool_call_id": "call_abc123",
    "result": {"status": "success", ...},
    "duration_ms": 1234,
    "timestamp": "2025-12-20T10:00:01Z"
}

{
    "type": "tool_error",
    "tool_name": "alert_admin",
    "tool_call_id": "call_abc123",
    "error": "Connection timeout",
    "timestamp": "2025-12-20T10:00:01Z"
}
```

---

## Approach 1: Async Event Queue with Custom Callback

### Description

Create a custom DSPY callback that pushes tool events to an async queue. The streaming generator polls the queue interleaved with token streaming.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    stream_generator()                        │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────┐     ┌───────────────────────────────┐  │
│  │  AsyncQueue    │◀────│  ToolEventCallback            │  │
│  │  (tool_events) │     │  - on_tool_start(): push      │  │
│  └────────┬───────┘     │  - on_tool_end(): push        │  │
│           │             └───────────────────────────────┘  │
│           │                                                 │
│           ▼                                                 │
│  ┌────────────────────────────────────────────────────────┐│
│  │  Interleaved Event Loop:                                ││
│  │   while streaming:                                      ││
│  │     - check tool_events queue → yield tool event        ││
│  │     - yield next token from LLM stream                  ││
│  │     - check heartbeat                                   ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# New file: utils/llm/tool_event_callback.py
import asyncio
from typing import Any, Optional
from dspy.utils.callback import BaseCallback

class ToolEventCallback(BaseCallback):
    """Callback that emits tool events to an async queue."""
    
    INTERNAL_TOOLS = {"finish", "Finish"}
    
    def __init__(self, event_queue: asyncio.Queue):
        super().__init__()
        self.event_queue = event_queue
    
    def on_tool_start(self, call_id: str, instance: Any, inputs: dict[str, Any]) -> None:
        tool_name = getattr(instance, "__name__", "unknown")
        if tool_name in self.INTERNAL_TOOLS:
            return
            
        event = {
            "type": "tool_start",
            "tool_name": tool_name,
            "tool_call_id": call_id,
            "arguments": inputs.get("args", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Put synchronously since this is called from sync context
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Drop event if queue is full
    
    def on_tool_end(self, call_id: str, outputs: Any, exception: Optional[Exception] = None) -> None:
        # Similar implementation for tool_end
        ...

# In agent.py stream_generator:
async def stream_generator():
    tool_event_queue = asyncio.Queue(maxsize=100)
    tool_callback = ToolEventCallback(tool_event_queue)
    
    # Add callback to DSPYInference
    inference_module = DSPYInference(
        ...,
        tool_callback=tool_callback,  # New parameter
    )
    
    async for chunk in inference_module.run_streaming(...):
        # Check for tool events first
        while not tool_event_queue.empty():
            tool_event = tool_event_queue.get_nowait()
            yield f"data: {json.dumps(tool_event)}\n\n"
        
        # Then yield the token
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
```

### Pros
- **Clean separation**: Callback logic is isolated from streaming logic
- **Minimal changes to existing code**: Extends existing callback pattern
- **Non-blocking**: Uses async queue for thread-safe communication
- **Ordered delivery**: Events are naturally ordered by when they occur

### Cons
- **Queue synchronization**: Need to handle sync → async boundary carefully
- **Potential event loss**: If queue is full or stream ends before queue is drained
- **Timing accuracy**: Small delay between actual event and emission
- **Complexity**: Requires managing queue lifecycle

### Effort Estimate
**Medium** - ~4-6 hours

---

## Approach 2: Instrumented Tool Wrappers

### Description

Wrap tools with instrumentation that directly emits SSE events through a shared event emitter. Tools emit events before/after execution.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 build_tool_wrappers_with_events()           │
├─────────────────────────────────────────────────────────────┤
│  def wrapped_tool(*args, **kwargs):                         │
│      event_emitter.emit(tool_start_event)  ──────┐          │
│      try:                                         │          │
│          result = original_tool(*args, **kwargs)  │          │
│          event_emitter.emit(tool_end_event)  ────┤          │
│          return result                            ▼          │
│      except Exception as e:               ┌──────────────┐  │
│          event_emitter.emit(tool_error)   │ SSE Stream   │  │
│          raise                            │ Generator    │  │
│                                           └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# New event emitter abstraction
class ToolEventEmitter:
    """Thread-safe event emitter for tool events."""
    
    def __init__(self):
        self._queue = asyncio.Queue()
        self._loop = None
    
    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
    
    def emit(self, event: dict):
        if self._loop:
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, event
            )
    
    async def get_events(self) -> AsyncGenerator[dict, None]:
        while True:
            try:
                event = self._queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                break

def build_tool_wrappers_with_events(
    user_id: str,
    event_emitter: ToolEventEmitter,
    tools: Optional[Iterable[Callable[..., Any]]] = None,
) -> list[Callable[..., Any]]:
    """Build tool wrappers that emit events."""
    
    raw_tools = list(tools) if tools else get_agent_tools()
    
    def _wrap_tool_with_events(tool: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(tool)
        def instrumented_tool(*args: Any, **kwargs: Any) -> Any:
            call_id = str(uuid.uuid4())
            start_time = time.monotonic()
            
            # Emit start event
            event_emitter.emit({
                "type": "tool_start",
                "tool_name": tool.__name__,
                "tool_call_id": call_id,
                "arguments": _sanitize_arguments(kwargs),
            })
            
            try:
                result = tool(*args, **kwargs)
                
                # Emit end event
                event_emitter.emit({
                    "type": "tool_end",
                    "tool_name": tool.__name__,
                    "tool_call_id": call_id,
                    "duration_ms": int((time.monotonic() - start_time) * 1000),
                    "result": _sanitize_result(result),
                })
                
                return result
            except Exception as e:
                event_emitter.emit({
                    "type": "tool_error",
                    "tool_name": tool.__name__,
                    "tool_call_id": call_id,
                    "error": str(e),
                })
                raise
        
        return instrumented_tool
    
    return [_wrap_tool_with_events(tool) for tool in raw_tools]
```

### Pros
- **Direct integration**: Events are emitted at the exact moment of tool execution
- **Simple mental model**: Each tool is wrapped with event logic
- **Precise timing**: No delay between action and event
- **Easy to extend**: Can add more metadata per-tool

### Cons
- **Invasive**: Requires modifying tool wrapper logic
- **Thread safety complexity**: Event emitter must be thread-safe
- **Tight coupling**: Tools now depend on event infrastructure
- **Duplication risk**: Event logic duplicated across wrappers

### Effort Estimate
**Medium** - ~4-5 hours

---

## Approach 3: Extended DSPY Callback with Streaming Integration

### Description

Extend the existing `LangFuseDSPYCallback` to also emit tool events through the streaming mechanism. This leverages the existing callback infrastructure.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Extended LangFuseDSPYCallback                   │
├─────────────────────────────────────────────────────────────┤
│  class CombinedCallback(LangFuseDSPYCallback):              │
│      def __init__(self, ..., stream_callback):              │
│          self.stream_callback = stream_callback  # Func     │
│                                                              │
│      def on_tool_start(self, ...):                          │
│          super().on_tool_start(...)  # LangFuse tracing     │
│          self.stream_callback({                             │
│              "type": "tool_start", ...                      │
│          })                                                  │
│                                                              │
│      def on_tool_end(self, ...):                            │
│          super().on_tool_end(...)  # LangFuse tracing       │
│          self.stream_callback({                             │
│              "type": "tool_end", ...                        │
│          })                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# Extend existing callback
class StreamingToolCallback(LangFuseDSPYCallback):
    """Callback that adds tool event streaming to LangFuse tracing."""
    
    def __init__(
        self,
        signature: type[dspy_Signature],
        event_queue: asyncio.Queue,
        trace_id: Optional[str] = None,
        parent_observation_id: Optional[str] = None,
    ):
        super().__init__(signature, trace_id, parent_observation_id)
        self._event_queue = event_queue
        self._tool_start_times: dict[str, float] = {}
    
    def on_tool_start(self, call_id: str, instance: Any, inputs: dict[str, Any]) -> None:
        # Call parent for LangFuse tracing
        super().on_tool_start(call_id, instance, inputs)
        
        tool_name = getattr(instance, "__name__", "unknown")
        if tool_name in self.INTERNAL_TOOLS:
            return
        
        self._tool_start_times[call_id] = time.monotonic()
        
        try:
            self._event_queue.put_nowait({
                "type": "tool_start",
                "tool_name": tool_name,
                "tool_call_id": call_id,
                "arguments": self._sanitize_inputs(inputs),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except asyncio.QueueFull:
            log.warning(f"Tool event queue full, dropping tool_start for {tool_name}")
    
    def on_tool_end(self, call_id: str, outputs: Any, exception: Optional[Exception] = None) -> None:
        # Call parent for LangFuse tracing
        super().on_tool_end(call_id, outputs, exception)
        
        start_time = self._tool_start_times.pop(call_id, None)
        duration_ms = int((time.monotonic() - start_time) * 1000) if start_time else None
        
        event_type = "tool_error" if exception else "tool_end"
        event = {
            "type": event_type,
            "tool_call_id": call_id,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if exception:
            event["error"] = str(exception)
        else:
            event["result"] = self._sanitize_output(outputs)
        
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning(f"Tool event queue full, dropping {event_type}")
```

### Pros
- **Leverages existing infrastructure**: Builds on `LangFuseDSPYCallback`
- **Single source of truth**: Tool events flow through one callback
- **Consistent tracing**: LangFuse and streaming events are synchronized
- **Minimal code duplication**: Reuses existing callback structure

### Cons
- **Callback complexity**: Single callback has multiple responsibilities
- **Inheritance chain**: Tight coupling to `LangFuseDSPYCallback` implementation
- **Testing complexity**: Need to test both LangFuse and streaming paths
- **Queue synchronization**: Still needs async queue bridge

### Effort Estimate
**Low-Medium** - ~3-4 hours

---

## Approach 4: Dual Stream Architecture

### Description

Use a separate WebSocket or SSE stream specifically for tool events. The frontend combines both the token stream and the tool event stream.

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Frontend                                 │
│  ┌─────────────────────────┐    ┌─────────────────────────┐   │
│  │ Token Stream Consumer   │    │ Tool Event Consumer     │   │
│  │ (SSE /agent/stream)     │    │ (SSE /agent/tools)      │   │
│  └───────────┬─────────────┘    └───────────┬─────────────┘   │
│              │                               │                  │
│              └───────────┬───────────────────┘                  │
│                          ▼                                      │
│               ┌──────────────────────┐                         │
│               │  Unified Event Store │                         │
│               │  (merge & order)     │                         │
│               └──────────────────────┘                         │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                         Backend                                 │
│  ┌─────────────────────────┐    ┌─────────────────────────┐   │
│  │ POST /agent/stream      │    │ GET /agent/tools/{id}   │   │
│  │ Token streaming         │    │ Tool event streaming    │   │
│  └───────────┬─────────────┘    └───────────┬─────────────┘   │
│              │                               │                  │
│              └───────────┬───────────────────┘                  │
│                          ▼                                      │
│               ┌──────────────────────┐                         │
│               │  Shared Event Bus    │                         │
│               │  (Redis/Memory)      │                         │
│               └──────────────────────┘                         │
└────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# New endpoint for tool event streaming
@router.get("/agent/tools/{conversation_id}")
async def agent_tool_events(
    conversation_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    """Stream tool execution events for a conversation."""
    
    auth_user = await get_authenticated_user(request, db)
    
    async def tool_event_stream():
        # Subscribe to tool events for this conversation
        async for event in tool_event_bus.subscribe(conversation_id):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        tool_event_stream(),
        media_type="text/event-stream",
    )

# Modified agent callback to publish to event bus
class ToolEventPublisher(BaseCallback):
    def __init__(self, conversation_id: uuid.UUID):
        self.conversation_id = conversation_id
    
    def on_tool_start(self, ...):
        tool_event_bus.publish(self.conversation_id, {...})
```

### Pros
- **Separation of concerns**: Clean split between token and tool streams
- **Independent scaling**: Tool events can be handled by different infrastructure
- **Frontend flexibility**: Can handle streams independently
- **WebSocket option**: Could use WebSocket for bidirectional communication

### Cons
- **Increased complexity**: Two streams to manage
- **Coordination overhead**: Frontend must correlate events
- **Race conditions**: Events might arrive out of order
- **Additional infrastructure**: May need event bus (Redis, etc.)
- **Connection overhead**: Two connections per client

### Effort Estimate
**High** - ~8-12 hours

---

## Recommendation

### Recommended Approach: Approach 3 (Extended DSPY Callback with Streaming Integration)

**Rationale:**

1. **Lowest Risk**: Extends existing, tested callback infrastructure
2. **Consistent Observability**: Tool events are automatically correlated with LangFuse traces
3. **Minimal Changes**: Only needs modifications to `dspy_langfuse.py` and `agent.py`
4. **Single Stream**: Keeps all events in one SSE stream for simpler frontend logic
5. **Ordered Delivery**: Events naturally interleave with tokens in execution order

### Implementation Plan

#### Phase 1: Create Streaming Tool Callback (2 hours)
1. Create `StreamingToolCallback` class extending `LangFuseDSPYCallback`
2. Add event queue integration
3. Add input/output sanitization helpers

#### Phase 2: Integrate with Agent Streaming (1.5 hours)
1. Modify `stream_generator()` to create and use event queue
2. Update `DSPYInference` to accept the new callback
3. Add interleaved event checking in stream loop

#### Phase 3: Testing (1.5 hours)
1. Add unit tests for `StreamingToolCallback`
2. Add E2E tests for tool event streaming
3. Test with actual tool execution (alert_admin)

#### Phase 4: Documentation & Cleanup (1 hour)
1. Update API documentation
2. Add frontend integration examples
3. Update test fixtures

### Total Estimated Effort: 6 hours

---

## Frontend Integration Guide

### SSE Event Handling

```typescript
const eventSource = new EventSource('/agent/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'start':
      // Initialize conversation UI
      setConversationId(data.conversation_id);
      setAvailableTools(data.tool_names);
      break;
      
    case 'token':
      // Append token to response
      appendToken(data.content);
      break;
      
    case 'tool_start':
      // Show tool execution indicator
      setActiveToolCall({
        id: data.tool_call_id,
        name: data.tool_name,
        status: 'running',
        args: data.arguments,
        startTime: data.timestamp,
      });
      break;
      
    case 'tool_end':
      // Update tool status
      updateToolCall(data.tool_call_id, {
        status: 'completed',
        result: data.result,
        duration: data.duration_ms,
      });
      break;
      
    case 'tool_error':
      // Show tool error
      updateToolCall(data.tool_call_id, {
        status: 'error',
        error: data.error,
      });
      break;
      
    case 'done':
      // Finalize conversation
      eventSource.close();
      break;
  }
};
```

### UI Component Example

```tsx
function ToolExecutionIndicator({ toolCall }) {
  return (
    <div className="tool-execution">
      <div className="tool-header">
        <span className="tool-icon">🔧</span>
        <span className="tool-name">{toolCall.name}</span>
        {toolCall.status === 'running' && <Spinner />}
      </div>
      
      {toolCall.status === 'running' && (
        <div className="tool-progress">
          Executing with: {JSON.stringify(toolCall.args)}
        </div>
      )}
      
      {toolCall.status === 'completed' && (
        <div className="tool-result success">
          ✓ Completed in {toolCall.duration}ms
        </div>
      )}
      
      {toolCall.status === 'error' && (
        <div className="tool-result error">
          ✗ Error: {toolCall.error}
        </div>
      )}
    </div>
  );
}
```

---

## Security Considerations

### Argument Sanitization

Tool arguments may contain sensitive data. Before streaming to the frontend:

```python
SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "credential"}

def _sanitize_arguments(args: dict) -> dict:
    """Remove sensitive values from tool arguments."""
    sanitized = {}
    for key, value in args.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_arguments(value)
        else:
            sanitized[key] = value
    return sanitized
```

### Result Sanitization

Tool results may also contain sensitive data:

```python
def _sanitize_result(result: Any) -> Any:
    """Sanitize tool result for streaming."""
    if isinstance(result, dict):
        # Remove known sensitive keys
        return {
            k: "[REDACTED]" if any(s in k.lower() for s in SENSITIVE_KEYS) else v
            for k, v in result.items()
        }
    return result
```

---

## Configuration

Add to `common/global_config.yaml`:

```yaml
agent_chat:
  streaming:
    # ... existing config ...
    tool_events:
      enabled: true
      # Maximum events to queue before dropping
      max_queue_size: 100
      # Include full arguments in events (may contain sensitive data)
      include_arguments: true
      # Include full results in events
      include_results: true
```

---

## Monitoring & Observability

Tool events are automatically traced in LangFuse through the parent callback. Additional metrics to consider:

1. **Tool execution latency**: Time from `tool_start` to `tool_end`
2. **Tool error rate**: Percentage of tool calls that result in errors
3. **Event queue depth**: Monitor queue fullness
4. **Event drop rate**: Track when events are dropped due to full queue

---

## Open Questions

1. **Should we persist tool calls to the database?**
   - Pro: Audit trail, replay capability
   - Con: Additional write overhead

2. **Should tool events be visible in conversation history?**
   - Pro: Transparency for users
   - Con: May clutter conversation display

3. **How should we handle long-running tools?**
   - Consider adding `tool_progress` events for tools > 5 seconds

4. **Should we stream tool arguments before execution?**
   - This could reveal intent before tool completes
   - May need configuration per-tool

---

## Appendix: Complete Event Schema

```json
{
  "tool_start": {
    "type": "tool_start",
    "tool_name": "string",
    "tool_call_id": "uuid",
    "arguments": "object",
    "timestamp": "ISO8601"
  },
  "tool_end": {
    "type": "tool_end",
    "tool_name": "string",
    "tool_call_id": "uuid",
    "result": "any",
    "duration_ms": "number",
    "timestamp": "ISO8601"
  },
  "tool_error": {
    "type": "tool_error",
    "tool_name": "string",
    "tool_call_id": "uuid",
    "error": "string",
    "duration_ms": "number",
    "timestamp": "ISO8601"
  }
}
```
