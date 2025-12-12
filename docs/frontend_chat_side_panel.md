## Frontend Chat Side Panel Specs

### Goals
- Provide lightweight in-app agent chat without leaving the current view.
- Keep context visible (current page) while letting users read/reply to the agent.
- Reduce interruption with clear unread cues and predictable focus/keyboard behavior.

### Layout
- **Placement:** Right-side slide-over panel on desktop; left-side slide-over on mobile; width ~380-420px on desktop, full width on mobile.
- **Header:** Conversation title, agent name/status, close button.
- **Body:** Scrollable message list (latest at bottom) with day dividers.
- **Composer:** Multiline text area, send button, attachment button (template-based upload), shortcuts hint.
- **Footer helpers:** Typing indicator region and connectivity status.

### Core Features
- **Message list:** Render speaker label (user vs agent) and message bubble. Support markdown rendering (text, headings, lists), code blocks, inline links, and agent tool outputs (structured blocks).
- **Send flow:** Press Enter to send, Shift+Enter for newline; send button disabled while empty or offline.
- **Streaming replies:** Stream agent/system messages; show live cursor and partial tokens.
- **Typing indicator:** Show “Agent is typing…” when composing; debounce to avoid flicker.
- **Message status:** Pending/sent/failed states with retry button on failure.
- **Inline actions:** Copy, react (👍/👎), and collapse long messages (“Show more” >8 lines).
- **Filters:** Toggle to show all messages or only agent/system messages.
- **Attachments:** Attachment button present; accept files based on provided template (e.g., allowed types/size); show drop-zone; hide upload behind capability flag until backend ready.

### Interactions
- **Open/close:** Close on explicit click or Esc; remember open state per page.
- **Scroll behavior:** Auto-scroll to bottom on new messages only if the user is near the bottom; otherwise show a “New messages” toast to jump down.
- **Keyboard:** Enter (send), Shift+Enter (newline), Cmd/Ctrl+F (toggle filter), Esc (close).
- **Focus:** Focus composer on open; preserve draft per conversation key (e.g., conversation_id + route).

### Data + State
- **Inputs (see agent routes for shapes):** conversation_id, user_id, agent_id, messages, capabilities (can_attach); keep UI-level assumptions minimal.
- **Local state:** draft text, unsent message queue, scroll anchor, filter mode.
- **Network:** Websocket/Server-Sent Events for live updates + REST fallback for history pagination; agent replies may stream.
- **Pagination:** Fetch latest 50 on open; infinite scroll up for older messages.

### Error + Offline
- **Offline mode:** Banner + disable send; queue drafts locally and auto-send when reconnected.
- **Send failure:** Mark bubble as failed with retry + copy-to-clipboard. Keep draft restored on error.
- **History load failure:** Show inline error with “Retry” and “Report” actions.

### Accessibility
- **ARIA:** Landmarks for header/body/composer; `aria-live="polite"` for new incoming messages.
- **Focus order:** Header → filter → list → composer → actions.
- **Keyboard:** All actions reachable via keyboard; visible focus rings.
- **Color/contrast:** Meet WCAG AA; support reduced motion (disable slide/typing shimmer).

### Performance & Resilience
- Virtualize long lists; throttle scroll events.
- De-bounce typing indicators and search queries.
- Cache recent conversations per session; hydrate from cache while fetching fresh data.
- Guard against duplicate message IDs; de-dup on arrival.

### Observability
- Emit events: panel_open/close, message_send, message_send_failed, message_receive, filter_changed, scroll_to_unread, retry_send.
- Include conversation_id, user_id, message_id, latency, offline flag, and error codes where applicable.
