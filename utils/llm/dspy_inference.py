import asyncio
from typing import Callable, Any, AsyncGenerator
import dspy
from common import global_config

from loguru import logger as log
from utils.llm.dspy_langfuse import LangFuseDSPYCallback


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
        trace_id: str | None = None,
        parent_observation_id: str | None = None,
        extra_callbacks: list[Any] | None = None,
    ) -> None:
        if tools is None:
            tools = []

        api_key = global_config.llm_api_key(model_name)

        # Build timeout configuration for LiteLLM (used by DSPY)
        # Format: (connect_timeout, read_timeout) or single timeout value
        timeout = global_config.llm_config.timeout.api_timeout_seconds

        self.lm = dspy.LM(
            model=model_name,
            api_key=api_key,
            cache=global_config.llm_config.cache_enabled,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,  # Add timeout to prevent hanging
            # Use LiteLLM's built-in retry mechanism instead of tenacity @retry decorator.
            # This retries only the LLM API calls, NOT tool executions, preventing
            # duplicate side effects when tools are called during ReAct inference.
            num_retries=global_config.llm_config.retry.max_attempts,
        )
        self.observe = observe
        if observe:
            # Initialize a LangFuseDSPYCallback for generation tracing
            self.callback = LangFuseDSPYCallback(
                pred_signature,
                trace_id=trace_id,
                parent_observation_id=parent_observation_id,
            )
        else:
            self.callback = None
        self.extra_callbacks = extra_callbacks or []

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

    async def run(
        self,
        **kwargs: Any,
    ) -> Any:
        try:
            # Get inference module (lazy init)
            _, inference_module_async = self._get_inference_module()

            # Use dspy.context() for async-safe configuration
            context_kwargs = {"lm": self.lm}
            callbacks: list[Any] = []
            if self.observe and self.callback:
                callbacks.append(self.callback)
            callbacks.extend(self.extra_callbacks)
            if callbacks:
                context_kwargs["callbacks"] = callbacks

            with dspy.context(**context_kwargs):
                result = await inference_module_async(**kwargs, lm=self.lm)

        except Exception as e:
            log.error(f"Error in run: {str(e)}")
            raise
        return result

    async def run_streaming(
        self,
        stream_field: str = "response",
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Run inference with streaming output.

        Args:
            stream_field: The output field to stream (default: "response")
            **kwargs: Input arguments for the signature

        Yields:
            str: Chunks of streamed text as they are generated
        """
        try:
            # Get inference module (lazy init) - use sync version for streamify
            inference_module, _ = self._get_inference_module()

            # Use dspy.context() for async-safe configuration
            context_kwargs = {"lm": self.lm}
            callbacks: list[Any] = []
            if self.observe and self.callback:
                callbacks.append(self.callback)
            callbacks.extend(self.extra_callbacks)
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
                # Check if it's an async generator by checking for __aiter__ method
                if hasattr(output_stream, "__aiter__"):
                    # It's an async generator, iterate asynchronously
                    async for chunk in output_stream:  # type: ignore
                        if isinstance(chunk, dspy.streaming.StreamResponse):  # type: ignore
                            yield chunk.chunk
                        elif isinstance(chunk, dspy.Prediction):
                            # Final prediction received, streaming complete
                            log.debug("Streaming completed")
                else:
                    # It's a sync generator, iterate synchronously
                    # To avoid blocking the event loop, we yield control periodically
                    for chunk in output_stream:  # type: ignore
                        # Yield control back to the event loop to prevent blocking
                        # This allows other coroutines to run (e.g., heartbeat checks)
                        await asyncio.sleep(0)

                        if isinstance(chunk, dspy.streaming.StreamResponse):  # type: ignore
                            yield chunk.chunk
                        elif isinstance(chunk, dspy.Prediction):
                            # Final prediction received, streaming complete
                            log.debug("Streaming completed")

        except Exception as e:
            log.error(f"Error in run_streaming: {str(e)}")
            raise e
