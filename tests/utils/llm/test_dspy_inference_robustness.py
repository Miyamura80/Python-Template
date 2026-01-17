import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from utils.llm.dspy_inference import DSPYInference
from litellm.exceptions import RateLimitError, ServiceUnavailableError, Timeout
import dspy

class MockSignature(dspy.Signature):
    input = dspy.InputField()
    output = dspy.OutputField()

def run_async(coro):
    return asyncio.run(coro)

def test_retry_on_rate_limit():
    async def _test():
        with patch("common.global_config.global_config.llm_api_key", return_value="fake-key"), \
             patch("common.global_config.global_config.default_llm.default_request_timeout", 1):

            inference = DSPYInference(pred_signature=MockSignature, observe=False)

            error = RateLimitError("Rate limit", llm_provider="openai", model="gpt-4")

            mock_method = AsyncMock(side_effect=[
                error,
                dspy.Prediction(output="Success")
            ])
            inference.inference_module_async = mock_method

            result = await inference.run(input="test")

            assert result.output == "Success"
            assert mock_method.call_count == 2

    run_async(_test())

def test_retry_on_timeout():
    async def _test():
        with patch("common.global_config.global_config.llm_api_key", return_value="fake-key"), \
             patch("common.global_config.global_config.default_llm.default_request_timeout", 1):

            inference = DSPYInference(pred_signature=MockSignature, observe=False)

            error = Timeout("Timeout", llm_provider="openai", model="gpt-4")

            mock_method = AsyncMock(side_effect=[
                error,
                dspy.Prediction(output="Success")
            ])
            inference.inference_module_async = mock_method

            result = await inference.run(input="test")

            assert result.output == "Success"
            assert mock_method.call_count == 2

    run_async(_test())

def test_fallback_logic():
    async def _test():
        with patch("common.global_config.global_config.llm_api_key", return_value="fake-key"):

            # Setup with fallback
            inference = DSPYInference(
                pred_signature=MockSignature,
                observe=False,
                model_name="primary-model",
                fallback_model="fallback-model"
            )

            async def side_effect(*args, **kwargs):
                lm = kwargs.get('lm')
                if lm.model == "primary-model":
                    raise ServiceUnavailableError("Down", llm_provider="openai", model="primary-model")
                elif lm.model == "fallback-model":
                    return dspy.Prediction(output="Fallback Success")
                else:
                    raise ValueError(f"Unknown model: {lm.model}")

            inference.inference_module_async = AsyncMock(side_effect=side_effect)

            result = await inference.run(input="test")

            assert result.output == "Fallback Success"

            # Primary model should have been retried max_attempts times (default 3)
            # Fallback model called once
            # Total 4
            assert inference.inference_module_async.call_count == 4

    run_async(_test())

def test_fallback_failure():
    async def _test():
        with patch("common.global_config.global_config.llm_api_key", return_value="fake-key"):

            # Setup with fallback where fallback also fails
            inference = DSPYInference(
                pred_signature=MockSignature,
                observe=False,
                model_name="primary-model",
                fallback_model="fallback-model"
            )

            async def side_effect(*args, **kwargs):
                lm = kwargs.get('lm')
                if lm.model == "primary-model":
                    raise ServiceUnavailableError("Down", llm_provider="openai", model="primary-model")
                elif lm.model == "fallback-model":
                    raise ServiceUnavailableError("Also Down", llm_provider="openai", model="fallback-model")
                else:
                    raise ValueError(f"Unknown model: {lm.model}")

            inference.inference_module_async = AsyncMock(side_effect=side_effect)

            # Execute and expect exception
            try:
                await inference.run(input="test")
                assert False, "Should have raised ServiceUnavailableError"
            except ServiceUnavailableError:
                pass

            # Primary called 3 times, Fallback called 3 times
            # Total 6
            assert inference.inference_module_async.call_count == 6

    run_async(_test())
