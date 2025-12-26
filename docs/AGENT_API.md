# Agent API Documentation

## Endpoint: Streaming Chat

**URL:** `POST /agent/stream`

This endpoint establishes a Server-Sent Events (SSE) connection to stream the agent's response, including text tokens and tool execution updates.

### Authentication

The endpoint requires the user to be authenticated via the session cookie.

### Request Body

Content-Type: `application/json`

```json
{
  "message": "Can you check the system status?",
  "context": "Optional context about the user or situation",
  "conversation_id": "optional-uuid-of-existing-conversation"
}
```

| Field | Type | Description |
|---|---|---|
| `message` | string | **Required**. The user's message to the agent. |
| `context` | string \| null | Optional additional context. |
| `conversation_id` | UUID \| null | Optional ID to continue an existing conversation. If omitted, a new conversation is created. |

### Response Format

The response is a stream of Server-Sent Events (`text/event-stream`). Each event is a JSON object prefixed with `data: `.

#### Event Types

The client should listen for the following `type` values in the JSON payload:

---

#### 1. `start`
Emitted at the very beginning of the stream.

```json
{
  "type": "start",
  "user_id": "user_123",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_title": "System Status Check",
  "tools_enabled": true,
  "tool_names": ["alert_admin"]
}
```

#### 2. `token`
Contains a chunk of the text response. These should be concatenated to form the assistant's message.

```json
{
  "type": "token",
  "content": "I "
}
```

#### 3. `tool_start`
Emitted when the agent decides to call a tool.

```json
{
  "type": "tool_start",
  "tool_call_id": "call_abc123",
  "tool_name": "alert_admin",
  "args": {
    "message": "User is reporting a system failure",
    "priority": "high"
  },
  "ts": "2023-10-27T10:00:00.123Z",
  "display": "Alerting admin..."  // Optional friendly text
}
```

#### 4. `tool_end`
Emitted when a tool execution completes successfully.

```json
{
  "type": "tool_end",
  "tool_call_id": "call_abc123",
  "tool_name": "alert_admin",
  "status": "success",
  "duration_ms": 150,
  "result": {
    "status": "sent",
    "ticket_id": 42
  },
  "ts": "2023-10-27T10:00:00.273Z",
  "display": "Admin alerted successfully" // Optional friendly text
}
```

#### 5. `tool_error`
Emitted if a tool execution fails.

```json
{
  "type": "tool_error",
  "tool_call_id": "call_abc123",
  "tool_name": "alert_admin",
  "status": "error",
  "duration_ms": 150,
  "error": {
    "message": "Connection timeout",
    "kind": "TimeoutError"
  },
  "ts": "2023-10-27T10:00:00.273Z"
}
```

#### 6. `conversation`
Emitted at the end of the stream with the full updated conversation object. This can be used to update the client's local state.

```json
{
  "type": "conversation",
  "conversation": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "System Status Check",
    "updated_at": "2023-10-27T10:00:05.000Z",
    "conversation": [
      {
        "role": "user",
        "content": "...",
        "created_at": "..."
      },
      {
        "role": "assistant",
        "content": "...",
        "created_at": "..."
      }
    ]
  }
}
```

#### 7. `warning`
Emitted for non-fatal issues (e.g., tool system failure causing fallback to normal chat).

```json
{
  "type": "warning",
  "code": "tool_fallback",
  "message": "Tool-enabled streaming encountered an issue. Continuing without tools."
}
```

#### 8. `error`
Emitted if a fatal error occurs during processing.

```json
{
  "type": "error",
  "message": "Something went wrong..."
}
```

#### 9. `done`
Emitted when the stream is complete.

```json
{
  "type": "done"
}
```

---

### Example Frontend Handling

```javascript
const response = await fetch('/agent/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: "Check server status" })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');

  // Keep the last incomplete line in the buffer
  buffer = lines.pop() || '';

  for (const line of lines) {
    if (line.trim() === '') continue;

    if (line.startsWith('data: ')) {
      try {
        const data = JSON.parse(line.slice(6));

        switch (data.type) {
          case 'token':
            // Append data.content to UI
            break;
          case 'tool_start':
            // Show tool indicator
            break;
          case 'tool_end':
            // Show tool result or hide indicator
            break;
          case 'done':
            // Stream finished
            break;
        }
      } catch (e) {
        console.error('Error parsing SSE data:', e);
      }
    }
  }
}
```
