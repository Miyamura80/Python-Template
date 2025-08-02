from contextvars import ContextVar

# Create a context variable for session_id
session_id: ContextVar[str | None] = ContextVar[str | None]("session_id", default=None)
