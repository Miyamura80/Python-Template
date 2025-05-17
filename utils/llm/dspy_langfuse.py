from dspy.utils.callback import BaseCallback
from langfuse.decorators import langfuse_context
from langfuse import Langfuse
from litellm import completion_cost
from langfuse.media import LangfuseMedia
from typing import Optional
import dspy
import contextvars
from loguru import logger

"""
NOTE: We use contextvars to store the current state of the callback, so it is thread-safe.
"""


# 1. Define a custom callback class that extends BaseCallback class
class LangFuseDSPYCallback(BaseCallback):
    def __init__(self, signature: dspy.Signature):
        super().__init__()
        # Use contextvars for per-call state
        self.current_system_prompt = contextvars.ContextVar("current_system_prompt")
        self.current_prompt = contextvars.ContextVar("current_prompt")
        self.current_completion = contextvars.ContextVar("current_completion")
        self.current_span = contextvars.ContextVar("current_span")
        self.model_name_at_span_creation = contextvars.ContextVar("model_name_at_span_creation")
        self.input_field_values = contextvars.ContextVar("input_field_values")
        # Initialize Langfuse client
        self.langfuse = Langfuse()
        self.input_field_names = signature.input_fields.keys()
        for input_field_name, input_field in signature.input_fields.items():
            if input_field.annotation == Optional[dspy.Image] or input_field.annotation == dspy.Image:
                pass # TODO: We need to handle media.

    def on_module_start(self, call_id, *args, **kwargs):
        inputs = kwargs.get("inputs")
        extracted_args = inputs["kwargs"]
        input_field_values = {}
        for input_field_name in self.input_field_names:
            if input_field_name in extracted_args:
                input_field_values[input_field_name] = extracted_args[input_field_name]
        self.input_field_values.set(input_field_values)

    def on_module_end(self, call_id, outputs, exception):
        metadata = {
            "existing_trace_id": langfuse_context.get_current_trace_id(),
            "parent_observation_id": langfuse_context.get_current_observation_id(),
        }
        outputs_extracted = {} # Default to empty dict
        if outputs is not None:
            try:
                outputs_extracted = {k: v for k, v in outputs.items()}
            except AttributeError:
                outputs_extracted = {"value": outputs}
            except Exception as e:
                outputs_extracted = {"error_extracting_module_output": str(e)}
        langfuse_context.update_current_observation(
            input=self.input_field_values.get({}),
            output=outputs_extracted,
            metadata=metadata
        )

    def on_lm_start(self, call_id, *args, **kwargs):
        # There is a double-trigger, so only count the first trigger.
        if self.current_span.get(None):
            return
        lm_instance = kwargs.get("instance")
        lm_dict = lm_instance.__dict__
        model_name = lm_dict.get("model")
        temperature = lm_dict.get("kwargs", {}).get("temperature")
        max_tokens = lm_dict.get("kwargs", {}).get("max_tokens")
        inputs = kwargs.get("inputs")
        messages = inputs.get("messages")
        assert messages[0].get("role") == "system"
        system_prompt = messages[0].get("content")
        assert messages[1].get("role") == "user"
        user_input = messages[1].get("content")
        self.current_system_prompt.set(system_prompt)
        self.current_prompt.set(user_input)
        self.model_name_at_span_creation.set(model_name)
        trace_id = langfuse_context.get_current_trace_id()
        parent_observation_id = langfuse_context.get_current_observation_id()
        span_obj = None
        if trace_id:
            span_obj = self.langfuse.generation(
                input=user_input,
                name=model_name,
                trace_id=trace_id,
                parent_observation_id=parent_observation_id,
                metadata={
                    "model": model_name,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                },
            )
        self.current_span.set(span_obj)

    def on_lm_end(self, call_id, outputs, exception, **kwargs):
        completion_content = None
        model_name_for_span = None
        usage_for_span = None
        level = "DEFAULT"
        status_message = None
        span = self.current_span.get(None)
        system_prompt = self.current_system_prompt.get(None)
        prompt = self.current_prompt.get(None)
        model_name_for_span = self.model_name_at_span_creation.get(None)
        # Use the model name stored at span creation as the primary source
        if exception:
            level = "ERROR"
            status_message = str(exception)
        elif outputs is None:
            level = "ERROR"
            status_message = "LM call returned None outputs without an explicit exception."
        elif isinstance(outputs, list):
            if outputs:
                completion_content = outputs[0]
            else:
                level = "WARNING"
                status_message = "LM call returned an empty list as outputs."
        else:
            try:
                if hasattr(outputs, "model") and outputs.model is not None:
                    model_name_for_span = outputs.model
                if (
                    outputs.choices
                    and outputs.choices[0]
                    and outputs.choices[0].message
                ):
                    completion_content = outputs.choices[0].message.content
                else:
                    level = "WARNING"
                    status_message = "LM output structure did not contain expected choices or message."
            except AttributeError as e:
                level = "ERROR"
                status_message = f"Error processing LM output structure: {e}. Output: {str(outputs)[:200]}"
            except Exception as e:
                level = "ERROR"
                status_message = f"Unexpected error processing LM output: {e}. Output: {str(outputs)[:200]}"
        # Calculate usage if we have the necessary information
        if (
            completion_content
            and system_prompt is not None
            and prompt is not None
            and model_name_for_span
        ):
            try:
                if hasattr(outputs, "usage"):
                    prompt_tokens = outputs.usage.prompt_tokens
                    completion_tokens = outputs.usage.completion_tokens
                    total_tokens = outputs.usage.total_tokens
                else:
                    prompt_tokens = len(system_prompt + prompt)
                    completion_tokens = len(completion_content)
                    total_tokens = prompt_tokens + completion_tokens
                total_cost = completion_cost(
                    model=model_name_for_span,
                    prompt=system_prompt + prompt,
                    completion=completion_content,
                )
                if span:
                    span.update(
                        usage_details={
                            "input": prompt_tokens,
                            "output": completion_tokens,
                            "cache_read_input_tokens": 0,
                            "total": total_tokens,
                        },
                        cost_details={
                            "input": total_cost * (prompt_tokens / total_tokens) if total_tokens else 0,
                            "output": total_cost * (completion_tokens / total_tokens) if total_tokens else 0,
                            "cache_read_input_tokens": 0.0,
                            "total": total_cost,
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to calculate usage/cost: {str(e)}")
                level = "WARNING"
                status_message = f"Usage/cost calculation failed: {str(e)}"
        else:
            missing_info = []
            if not completion_content:
                missing_info.append("completion content")
            if not system_prompt:
                missing_info.append("system prompt")
            if not prompt:
                missing_info.append("user prompt")
            if not model_name_for_span:
                missing_info.append("model name")
            logger.warning(
                f"Missing required information for usage/cost calculation: {', '.join(missing_info)}"
            )
        if span:
            end_args = {
                "output": completion_content,
                "model": model_name_for_span,
                "level": level,
                "status_message": status_message,
            }
            final_end_args = {
                k: v
                for k, v in end_args.items()
                if v is not None or k in ["output", "model", "level", "status_message"]
            }
            span.end(**final_end_args)
            self.current_span.set(None)
        if level == "OK" and completion_content is not None:
            self.current_completion.set(completion_content)
