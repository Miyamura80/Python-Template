from tests.test_template import TestTemplate
from src.api.routes.agent.agent import serialize_history


class DummyMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class TestAgentHistorySerialization(TestTemplate):
    def test_serialize_history_limits_and_orders(self):
        messages = [
            DummyMessage("user", "m1"),
            DummyMessage("assistant", "m2"),
            DummyMessage("user", "m3"),
            DummyMessage("assistant", "m4"),
        ]

        history = serialize_history(messages, history_limit=3)

        assert [item["content"] for item in history] == ["m2", "m3", "m4"]
        assert [item["role"] for item in history] == [
            "assistant",
            "user",
            "assistant",
        ]

    def test_serialize_history_zero_limit_is_empty(self):
        messages = [DummyMessage("user", "only")]

        history = serialize_history(messages, history_limit=0)

        assert history == []
