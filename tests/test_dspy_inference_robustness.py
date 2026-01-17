import asyncio

import dspy

from common import global_config
from tests.test_template import TestTemplate
from utils.llm.dspy_inference import DSPYInference


class DummySignature(dspy.Signature):
    input_text: str = dspy.InputField()
    output_text: str = dspy.OutputField()


class FakeRateLimitError(Exception):
    def __init__(self, message: str = "rate limit") -> None:
        super().__init__(message)
        self.status_code = 429


class FakeServiceUnavailableError(Exception):
    def __init__(self, message: str = "service unavailable") -> None:
        super().__init__(message)
        self.status_code = 503


class TestDspyInferenceRobustness(TestTemplate):
    def _stub_dspy(self, monkeypatch) -> None:
        class FakeLM:
            def __init__(
                self,
                *,
                model: str,
                api_key: str,
                cache: bool,
                temperature: float,
                max_tokens: int,
            ) -> None:
                self.model = model
                self.kwargs = {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

        monkeypatch.setattr(dspy, "LM", FakeLM)
        monkeypatch.setattr(dspy, "configure", lambda **kwargs: None)
        monkeypatch.setattr(dspy, "ReAct", lambda *args, **kwargs: object())
        monkeypatch.setattr(dspy, "Predict", lambda *args, **kwargs: object())
        monkeypatch.setattr(dspy, "asyncify", lambda module: module)

    def test_retries_on_rate_limit_then_succeeds(self, monkeypatch) -> None:
        self._stub_dspy(monkeypatch)
        inference = DSPYInference(
            pred_signature=DummySignature,
            observe=False,
        )

        attempts = {"count": 0}
        sleep_durations: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_durations.append(seconds)

        async def fake_inference(**kwargs):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise FakeRateLimitError("too many requests")
            return {"ok": True}

        inference._sleep = fake_sleep
        inference.inference_module_async = fake_inference

        result = asyncio.run(inference.run(input_text="hello"))

        assert result == {"ok": True}
        assert attempts["count"] == 3
        assert len(sleep_durations) == 2
        assert sleep_durations[1] >= sleep_durations[0]

    def test_fallback_when_gemini_down(self, monkeypatch) -> None:
        self._stub_dspy(monkeypatch)
        inference = DSPYInference(
            pred_signature=DummySignature,
            observe=False,
        )

        assert inference.fallback_lm is not None

        primary_calls = {"count": 0}
        fallback_calls = {"count": 0}

        async def fake_sleep(seconds: float) -> None:
            return None

        async def fake_inference(**kwargs):
            lm = kwargs.get("lm")
            if lm is inference.primary_lm:
                primary_calls["count"] += 1
                raise FakeServiceUnavailableError()
            fallback_calls["count"] += 1
            return {"fallback": True}

        inference._sleep = fake_sleep
        inference.inference_module_async = fake_inference

        result = asyncio.run(inference.run(input_text="hello"))

        assert result == {"fallback": True}
        assert primary_calls["count"] == global_config.llm_config.retry.max_attempts
        assert fallback_calls["count"] == 1

    def test_thinking_timeout_selection(self, monkeypatch) -> None:
        self._stub_dspy(monkeypatch)
        inference = DSPYInference(
            pred_signature=DummySignature,
            observe=False,
            model_name="gemini-thinking",
        )

        default_timeout = global_config.llm_config.timeout.default_seconds
        thinking_timeout = global_config.llm_config.timeout.thinking_seconds

        assert inference._timeout_seconds_for_model("gpt-4o-mini") == default_timeout
        assert inference._timeout_seconds_for_model("gemini-thinking") == thinking_timeout
