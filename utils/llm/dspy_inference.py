import asyncio
import os
from collections.abc import AsyncGenerator, Callable
from typing import Any

import dspy
from litellm.exceptions import RateLimitError, ServiceUnavailableError
from loguru import logger as log
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common import global_config
from common.flags import client


def _langfuse_configured() -> bool:
    """Check if LangFuse credentials are present in environment."""
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
    )


class DSPYInference:
    def __init__(
        self,
        pred_signature: type[dspy.Signature],
        tools: list[Callable[..., Any]] | None = None,
        observe: bool = True,
        model_name: str = global_config.default_llm.default_model,
        fallback_model_name: str | None = global_config.default_llm.fallback_model,
        temperature: float = global_config.default_llm.default_temperature,
        max_tokens: int = global_config.default_llm.default_max_tokens,
        max_iters: int = 5,
        trace_id: str | None = None,
        parent_observation_id: str | None = None,
    ) -> None:
        if tools is None:
            tools = []

        self.lm = self._build_lm(model_name, temperature, max_tokens)
        self.fallback_model_name = (
            fallback_model_name
            if fallback_model_name and fallback_model_name != model_name
            else None
        )
        self.fallback_lm = (
            self._build_lm(self.fallback_model_name, temperature, max_tokens)
            if self.fallback_model_name is not None
            else None
        )
        self.dspy_config: dict[str, Any] = {"lm": self.lm}
        if observe and _langfuse_configured():
            from utils.llm.dspy_langfuse import LangFuseDSPYCallback

            self.callback = LangFuseDSPYCallback(
                pred_signature,
                trace_id=trace_id,
                parent_observation_id=parent_observation_id,
            )
            self.dspy_config["callbacks"] = [self.callback]
        else:
            self.callback = None
        self._use_langfuse_observe = observe and _langfuse_configured()

        # Store tools and signature for lazy initialization
        self.tools = tools
        self.pred_signature = pred_signature
        self.max_iters = max_iters
        self._inference_module = None
        self._inference_module_async = None

    def _get_inference_module(self):
        """Lazy initialization of inference module."""
        if self._inference_module is None:
            # Agent Initialization
            if len(self.tools) > 0:
                self._inference_module = dspy.ReAct(
                    self.pred_signature,
                    tools=self.tools,
                    max_iters=self.max_iters,
                )
            else:
                self._inference_module = dspy.Predict(self.pred_signature)
            self._inference_module_async = dspy.asyncify(self._inference_module)
        return self._inference_module, self._inference_module_async

    @retry(
        retry=retry_if_exception_type((RateLimitError, ServiceUnavailableError)),
        stop=stop_after_attempt(global_config.llm_config.retry.max_attempts),
        wait=wait_exponential(
            multiplier=global_config.llm_config.retry.min_wait_seconds,
            max=global_config.llm_config.retry.max_wait_seconds,
        ),
        before_sleep=lambda retry_state: log.warning(
            "Retrying due to LLM error "
            f"{retry_state.outcome.exception().__class__.__name__}. "
            f"Attempt {retry_state.attempt_number}"
        ),
    )
    async def _run_with_retry(
        self,
        lm: dspy.LM,
        extra_callbacks: list[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        _, inference_module_async = self._get_inference_module()
        context_kwargs: dict[str, Any] = {"lm": lm}
        callbacks: list[Any] = []
        if self._use_langfuse_observe and self.callback:
            callbacks.append(self.callback)
        if extra_callbacks:
            callbacks.extend(extra_callbacks)
        if callbacks:
            context_kwargs["callbacks"] = callbacks
        with dspy.context(**context_kwargs):
            return await inference_module_async(**kwargs, lm=lm)

    def _build_lm(
        self,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> dspy.LM:
        api_key = global_config.llm_api_key(model_name)
        timeout = (
            global_config.llm_config.timeout.api_timeout_seconds
            if global_config.llm_config.timeout
            else None
        )
        lm_kwargs: dict[str, Any] = {
            "model": model_name,
            "api_key": api_key,
            "cache": global_config.llm_config.cache_enabled,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if timeout:
            lm_kwargs["timeout"] = timeout
        return dspy.LM(**lm_kwargs)

    async def _run_inner(
        self,
        extra_callbacks: list[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        try:
            result = await self._run_with_retry(
                self.lm, extra_callbacks=extra_callbacks, **kwargs
            )
        except (RateLimitError, ServiceUnavailableError) as e:
            # Check feature flag for fallback logic
            if not client.get_boolean_value("enable_llm_fallback", True):
                log.warning("LLM fallback disabled by feature flag. Propagating error.")
                raise

            if not self.fallback_lm:
                log.error(f"{e.__class__.__name__} without fallback: {str(e)}")
                raise
            log.warning(
                f"Primary model unavailable; falling back to {self.fallback_model_name}"
            )
            try:
                result = await self._run_with_retry(
                    self.fallback_lm, extra_callbacks=extra_callbacks, **kwargs
                )
            except (RateLimitError, ServiceUnavailableError) as fallback_error:
                log.error(f"Fallback model failed: {fallback_error.__class__.__name__}")
                raise
        except (RuntimeError, ValueError, TypeError) as e:
            log.error(f"Error in run: {str(e)}")
            raise
        return result

    async def run(
        self,
        extra_callbacks: list[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        if self._use_langfuse_observe:
            from langfuse import observe as langfuse_observe

            return await langfuse_observe()(self._run_inner)(
                extra_callbacks=extra_callbacks, **kwargs
            )
        return await self._run_inner(extra_callbacks=extra_callbacks, **kwargs)

    async def run_streaming(
        self,
        stream_field: str = "response",
        extra_callbacks: list[Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Run inference with streaming output.

        Args:
            stream_field: The output field to stream (default: "response")
            extra_callbacks: Optional additional callbacks
            **kwargs: Input arguments for the signature

        Yields:
            str: Chunks of streamed text as they are generated
        """
        try:
            # Get inference module (lazy init) - use sync version for streamify
            inference_module, _ = self._get_inference_module()

            # Use dspy.context() for async-safe configuration
            context_kwargs: dict[str, Any] = {"lm": self.lm}
            callbacks: list[Any] = []
            if self._use_langfuse_observe and self.callback:
                callbacks.append(self.callback)
            if extra_callbacks:
                callbacks.extend(extra_callbacks)
            if callbacks:
                context_kwargs["callbacks"] = callbacks

            with dspy.context(**context_kwargs):
                # Create a streaming version of the inference module
                stream_listener = dspy.streaming.StreamListener(  # type: ignore
                    signature_field_name=stream_field
                )
                stream_module = dspy.streamify(
                    inference_module,
                    stream_listeners=[stream_listener],
                )

                # Execute the streaming module
                output_stream = stream_module(**kwargs)  # type: ignore

                # Yield chunks as they arrive
                if hasattr(output_stream, "__aiter__"):
                    async for chunk in output_stream:  # type: ignore
                        if isinstance(chunk, dspy.streaming.StreamResponse):  # type: ignore
                            yield chunk.chunk
                        elif isinstance(chunk, dspy.Prediction):
                            log.debug("Streaming completed")
                else:
                    for chunk in output_stream:  # type: ignore
                        await asyncio.sleep(0)
                        if isinstance(chunk, dspy.streaming.StreamResponse):  # type: ignore
                            yield chunk.chunk
                        elif isinstance(chunk, dspy.Prediction):
                            log.debug("Streaming completed")

        except Exception as e:
            log.error(f"Error in run_streaming: {str(e)}")
            raise
