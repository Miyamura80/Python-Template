from datetime import datetime

from tests.test_template import TestTemplate
from utils.llm.tool_display import tool_display
from utils.llm.tool_streaming_callback import ToolStreamingCallback


class TestToolStreamingCallback(TestTemplate):
    def test_emits_tool_start_and_tool_end_with_sanitization(self):
        events: list[dict] = []

        def emit(event: dict) -> None:
            events.append(event)

        @tool_display("Doing the thing…")
        def my_tool(api_key: str, issue_description: str) -> dict:
            _ = (api_key, issue_description)
            return {
                "status": "ok",
                "token": "super-secret",
                "nested": {"cookie": "abc", "value": "ok"},
                "big": "x" * 5000,
            }

        cb = ToolStreamingCallback(emit=emit)

        cb.on_tool_start(
            call_id="call_123",
            instance=my_tool,
            inputs={"args": {"api_key": "sk-live", "issue_description": "hi"}},
        )
        cb.on_tool_end(call_id="call_123", outputs=my_tool("sk-live", "hi"))

        assert len(events) == 2

        start = events[0]
        assert start["type"] == "tool_start"
        assert start["tool_call_id"] == "call_123"
        assert start["tool_name"] == "my_tool"
        assert start["display"] == "Doing the thing…"
        assert start["args"]["api_key"] == "[REDACTED]"
        assert start["args"]["issue_description"] == "hi"
        datetime.fromisoformat(start["ts"].replace("Z", "+00:00"))

        end = events[1]
        assert end["type"] == "tool_end"
        assert end["tool_call_id"] == "call_123"
        assert end["tool_name"] == "my_tool"
        assert end["display"] == "Doing the thing…"
        assert end["status"] == "success"
        assert isinstance(end["duration_ms"], int)
        assert end["duration_ms"] >= 0
        assert end["result"]["token"] == "[REDACTED]"
        assert end["result"]["nested"]["cookie"] == "[REDACTED]"
        assert end["result"]["nested"]["value"] == "ok"
        assert isinstance(end["result"]["big"], str)
        assert len(end["result"]["big"]) <= 2048
        datetime.fromisoformat(end["ts"].replace("Z", "+00:00"))

    def test_emits_tool_error(self):
        events: list[dict] = []

        def emit(event: dict) -> None:
            events.append(event)

        @tool_display(lambda args: f"Working on {args.get('job', '')}…")
        def my_tool(job: str) -> str:
            _ = job
            raise ValueError("boom")

        cb = ToolStreamingCallback(emit=emit)

        cb.on_tool_start(
            call_id="call_err",
            instance=my_tool,
            inputs={"args": {"job": "test"}},
        )
        cb.on_tool_end(call_id="call_err", outputs=None, exception=ValueError("boom"))

        assert len(events) == 2
        assert events[0]["type"] == "tool_start"
        err = events[1]
        assert err["type"] == "tool_error"
        assert err["tool_call_id"] == "call_err"
        assert err["tool_name"] == "my_tool"
        assert err["status"] == "error"
        assert err["display"] == "Working on test…"
        assert err["error"]["kind"] == "ValueError"
        assert "boom" in err["error"]["message"]
        assert isinstance(err["duration_ms"], int)
        assert err["duration_ms"] >= 0
