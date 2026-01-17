from typing import Callable, Any
import dspy
from common import global_config

from loguru import logger as log
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from utils.llm.dspy_langfuse import LangFuseDSPYCallback
from litellm.exceptions import ServiceUnavailableError, RateLimitError, Timeout
from langfuse.decorators import observe  # type: ignore


class DSPYInference:
    def __init__(
        self,
        pred_signature: type[dspy.Signature],
        tools: list[Callable[..., Any]] | None = None,
        observe: bool = True,
        model_name: str = global_config.default_llm.default_model,
        fallback_model: str | None = global_config.default_llm.fallback_model,
        temperature: float = global_config.default_llm.default_temperature,
        max_tokens: int = global_config.default_llm.default_max_tokens,
        request_timeout: int = global_config.default_llm.default_request_timeout,
        max_iters: int = 5,
    ) -> None:
        if tools is None:
            tools = []

        api_key = global_config.llm_api_key(model_name)
        self.lm = dspy.LM(
            model=model_name,
            api_key=api_key,
            cache=global_config.llm_config.cache_enabled,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=request_timeout,
        )

        self.fallback_lm = None
        if fallback_model:
            try:
                fallback_api_key = global_config.llm_api_key(fallback_model)
                self.fallback_lm = dspy.LM(
                    model=fallback_model,
                    api_key=fallback_api_key,
                    cache=global_config.llm_config.cache_enabled,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=request_timeout,
                )
            except Exception as e:
                log.warning(f"Failed to initialize fallback model {fallback_model}: {e}")

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
        retry=retry_if_exception_type((ServiceUnavailableError, RateLimitError, Timeout)),
        stop=stop_after_attempt(global_config.llm_config.retry.max_attempts),
        wait=wait_exponential(
            multiplier=global_config.llm_config.retry.min_wait_seconds,
            max=global_config.llm_config.retry.max_wait_seconds,
        ),
        before_sleep=lambda retry_state: log.warning(
            f"Retrying due to LLM Error ({retry_state.outcome.exception()}). Attempt {retry_state.attempt_number}"
        ),
        reraise=True,
    )
    async def _run_inference(self, lm, **kwargs) -> Any:
        return await self.inference_module_async(**kwargs, lm=lm)

    @observe()
    async def run(
        self,
        **kwargs: Any,
    ) -> Any:
        try:
            # user_id is passed if the pred_signature requires it.
            result = await self._run_inference(lm=self.lm, **kwargs)
        except Exception as e:
            if self.fallback_lm:
                log.warning(f"Primary model failed: {e}. Switching to fallback model.")
                try:
                    result = await self._run_inference(lm=self.fallback_lm, **kwargs)
                except Exception as fallback_error:
                    log.error(f"Fallback model also failed: {fallback_error}")
                    raise fallback_error
            else:
                log.error(f"Error in run: {str(e)}")
                raise
        return result
