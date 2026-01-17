import asyncio
from unittest.mock import AsyncMock, patch
from utils.llm.dspy_inference import DSPYInference
from litellm.exceptions import RateLimitError, ServiceUnavailableError, Timeout
import dspy

class MockSignature(dspy.Signature):
    """A mock DSPy signature for testing purposes."""
    input = dspy.InputField()
    output = dspy.OutputField()

def run_async(coro):
    """Helper to run async test functions."""
    return asyncio.run(coro)

def test_retry_on_rate_limit():
    """
    Tests that the DSPYInference class correctly retries operations when encountering
    a RateLimitError from the LLM provider.

    It mocks the underlying async inference call to raise a RateLimitError on the first
    attempt and succeed on the second. It verifies that:
    1. The operation eventually succeeds.
    2. The inference method was called twice (initial attempt + 1 retry).
    """
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
    """
    Tests that the DSPYInference class correctly retries operations when encountering
    a Timeout error.

    It mocks the underlying async inference call to raise a Timeout on the first
    attempt and succeed on the second. It verifies that:
    1. The operation eventually succeeds.
    2. The inference method was called twice.
    """
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
    """
    Tests the model fallback mechanism.

    It configures a primary model and a fallback model. It mocks the inference call
    to simulate the primary model failing with a ServiceUnavailableError (which triggers retries).
    After the primary model's retries are exhausted, the system should switch to the fallback model.

    It verifies that:
    1. The operation succeeds using the fallback model.
    2. The total call count reflects the primary model's retries + the successful fallback attempt.
    """
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
    """
    Tests the scenario where both the primary and fallback models fail.

    It mocks both models to raise ServiceUnavailableError.

    It verifies that:
    1. The ServiceUnavailableError is ultimately raised to the caller.
    2. Both primary and fallback models were attempted (with their respective retries).
    """
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
