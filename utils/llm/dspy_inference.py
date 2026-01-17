import asyncio
from typing import Callable, Any

import dspy
from common import global_config
from loguru import logger as log
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)
from utils.llm.dspy_langfuse import LangFuseDSPYCallback
from litellm.exceptions import ServiceUnavailableError
from langfuse.decorators import observe  # type: ignore
from src.utils.logging_config import setup_logging

try:
    from litellm.exceptions import RateLimitError, Timeout, APIConnectionError, APIError
except ImportError:  # pragma: no cover - defensive for older litellm versions
    RateLimitError = None
    Timeout = None
    APIConnectionError = None
    APIError = None

setup_logging()


class DSPYInference:
    def __init__(
        self,
        pred_signature: type[dspy.Signature],
        tools: list[Callable[..., Any]] | None = None,
        observe: bool = True,
        model_name: str = global_config.default_llm.default_model,
        temperature: float = global_config.default_llm.default_temperature,
        max_tokens: int = global_config.default_llm.default_max_tokens,
        max_iters: int = 5,
    ) -> None:
        if tools is None:
            tools = []

        self.primary_model_name = model_name
        self.primary_lm = self._build_lm(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.lm = self.primary_lm
        self.fallback_model_name = self._resolve_fallback_model(model_name)
        self.fallback_lm = None
        if self.fallback_model_name:
            self.fallback_lm = self._build_lm(
                model_name=self.fallback_model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        self._sleep = asyncio.sleep
        if observe:
            # Initialize a LangFuseDSPYCallback and configure the LM instance for generation tracing
            self.callback = LangFuseDSPYCallback(pred_signature)
            dspy.configure(lm=self.primary_lm, callbacks=[self.callback])
        else:
            dspy.configure(lm=self.primary_lm)

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

    def _build_lm(
        self,
        *,
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

    def _resolve_fallback_model(self, model_name: str) -> str | None:
        fallback_config = global_config.llm_config.fallback
        if not fallback_config.enabled:
            return None
        if "gemini" not in model_name.lower():
            return None
        fallback_model = fallback_config.gemini_model.strip()
        if not fallback_model:
            return None
        if fallback_model.lower() == model_name.lower():
            return None
        try:
            global_config.llm_api_key(fallback_model)
        except ValueError as exc:
            log.warning(
                f"Fallback model API key not configured: {fallback_model}. "
                f"Disabling fallback. Error: {exc}"
            )
            return None
        return fallback_model

    def _iter_exception_chain(
        self, exc: BaseException
    ) -> list[BaseException]:
        seen: set[int] = set()
        chain: list[BaseException] = []
        current = exc
        while current and id(current) not in seen:
            chain.append(current)
            seen.add(id(current))
            current = current.__cause__ or current.__context__
        return chain

    def _exception_status_code(self, exc: BaseException) -> int | None:
        for attr in ["status_code", "status"]:
            value = getattr(exc, attr, None)
            if isinstance(value, int):
                return value
        response = getattr(exc, "response", None)
        if response is not None:
            response_status = getattr(response, "status_code", None)
            if isinstance(response_status, int):
                return response_status
        return None

    def _is_rate_limit_error(self, exc: BaseException) -> bool:
        if RateLimitError and isinstance(exc, RateLimitError):
            return True
        status_code = self._exception_status_code(exc)
        if status_code == 429:
            return True
        message = str(exc).lower()
        return (
            "rate limit" in message
            or "too many requests" in message
            or "http 429" in message
        )

    def _is_timeout_error(self, exc: BaseException) -> bool:
        if isinstance(exc, asyncio.TimeoutError):
            return True
        if Timeout and isinstance(exc, Timeout):
            return True
        status_code = self._exception_status_code(exc)
        if status_code == 408:
            return True
        message = str(exc).lower()
        return "timeout" in message or "timed out" in message

    def _is_service_unavailable_error(self, exc: BaseException) -> bool:
        if isinstance(exc, ServiceUnavailableError):
            return True
        status_code = self._exception_status_code(exc)
        if status_code in {502, 503, 504}:
            return True
        message = str(exc).lower()
        return (
            "service unavailable" in message
            or "bad gateway" in message
            or "gateway timeout" in message
        )

    def _is_retryable_exception(self, exc: BaseException) -> bool:
        for candidate in self._iter_exception_chain(exc):
            if self._is_rate_limit_error(candidate):
                return True
            if self._is_timeout_error(candidate):
                return True
            if self._is_service_unavailable_error(candidate):
                return True
            if APIConnectionError and isinstance(candidate, APIConnectionError):
                return True
            if APIError and isinstance(candidate, APIError):
                status_code = self._exception_status_code(candidate)
                if status_code and status_code >= 500:
                    return True
        return False

    def _should_fallback(self, exc: BaseException, model_name: str) -> bool:
        if not self.fallback_lm or not self.fallback_model_name:
            return False
        if "gemini" not in model_name.lower():
            return False
        return self._is_retryable_exception(exc)

    def _is_thinking_model(self, model_name: str) -> bool:
        markers = global_config.llm_config.timeout.thinking_model_markers
        model_name_lower = model_name.lower()
        return any(marker.lower() in model_name_lower for marker in markers)

    def _timeout_seconds_for_model(self, model_name: str) -> int:
        timeout_config = global_config.llm_config.timeout
        if self._is_thinking_model(model_name):
            return timeout_config.thinking_seconds
        return timeout_config.default_seconds

    def _log_retry(self, retry_state: Any) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        reason = (
            f"{type(exc).__name__}: {exc}" if exc else "unknown error"
        )
        log.warning(
            f"Retrying LLM call (attempt {retry_state.attempt_number}) "
            f"due to {reason}"
        )

    async def _call_with_timeout(
        self,
        *,
        lm: dspy.LM,
        timeout_seconds: int,
        **kwargs: Any,
    ) -> Any:
        try:
            return await asyncio.wait_for(
                self.inference_module_async(**kwargs, lm=lm),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            log.warning(
                f"LLM call timed out after {timeout_seconds} seconds."
            )
            raise

    async def _run_with_retry(
        self,
        *,
        lm: dspy.LM,
        model_name: str,
        **kwargs: Any,
    ) -> Any:
        timeout_seconds = self._timeout_seconds_for_model(model_name)
        retrying = AsyncRetrying(
            retry=retry_if_exception(self._is_retryable_exception),
            stop=stop_after_attempt(global_config.llm_config.retry.max_attempts),
            wait=wait_exponential(
                multiplier=global_config.llm_config.retry.min_wait_seconds,
                max=global_config.llm_config.retry.max_wait_seconds,
            ),
            before_sleep=self._log_retry,
            reraise=True,
            sleep=self._sleep,
        )
        async for attempt in retrying:
            with attempt:
                return await self._call_with_timeout(
                    lm=lm,
                    timeout_seconds=timeout_seconds,
                    **kwargs,
                )

    @observe()
    async def run(
        self,
        **kwargs: Any,
    ) -> Any:
        try:
            # user_id is passed if the pred_signature requires it.
            return await self._run_with_retry(
                lm=self.primary_lm,
                model_name=self.primary_model_name,
                **kwargs,
            )
        except Exception as exc:
            if self._should_fallback(exc, self.primary_model_name):
                log.warning(
                    "Primary model failed; falling back to "
                    f"{self.fallback_model_name}."
                )
                return await self._run_with_retry(
                    lm=self.fallback_lm,
                    model_name=self.fallback_model_name,
                    **kwargs,
                )
            log.error(f"Error in run: {str(exc)}")
            raise
