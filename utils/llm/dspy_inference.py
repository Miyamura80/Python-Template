from collections.abc import Callable
from typing import Any

import dspy
from langfuse import observe
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
from utils.llm.dspy_langfuse import LangFuseDSPYCallback


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
        if observe:
            # Initialize a LangFuseDSPYCallback and configure the LM instance for generation tracing
            self.callback = LangFuseDSPYCallback(pred_signature)
            dspy.configure(lm=self.lm, callbacks=[self.callback])
        else:
            dspy.configure(lm=self.lm)

        # Agent Intiialization
        if len(tools) > 0:
            self.inference_module = dspy.ReAct(
                pred_signature,
                tools=tools,  # Uses tools as passed, no longer appends read_memory
                max_iters=max_iters,
            )
        else:
            self.inference_module = dspy.Predict(pred_signature)
        self.inference_module_async: Callable[..., Any] = dspy.asyncify(
            self.inference_module
        )

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
        **kwargs: Any,
    ) -> Any:
        return await self.inference_module_async(**kwargs, lm=lm)

    def _build_lm(
        self,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> dspy.LM:
        api_key = global_config.llm_api_key(model_name)
        return dspy.LM(
            model=model_name,
            api_key=api_key,
            cache=global_config.llm_config.cache_enabled,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @observe()
    async def run(
        self,
        **kwargs: Any,
    ) -> Any:
        try:
            # user_id is passed if the pred_signature requires it.
            result = await self._run_with_retry(self.lm, **kwargs)
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
                result = await self._run_with_retry(self.fallback_lm, **kwargs)
            except (RateLimitError, ServiceUnavailableError) as fallback_error:
                log.error(f"Fallback model failed: {fallback_error.__class__.__name__}")
                raise
        except (RuntimeError, ValueError, TypeError) as e:
            log.error(f"Error in run: {str(e)}")
            raise
        return result
