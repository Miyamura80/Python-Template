from dspy.utils.callback import BaseCallback
from langfuse.decorators import langfuse_context  # type: ignore
from langfuse.client import Langfuse, StatefulGenerationClient  # type: ignore
from litellm.cost_calculator import completion_cost  # type: ignore
from typing import Optional, Any, Literal
from pydantic import BaseModel, ValidationError, Field
from dspy.adapters import Image as dspy_Image
from dspy.signatures import Signature as dspy_Signature
import contextvars
from loguru import logger as log


# Pydantic models for parsing the 'outputs' dictionary when it's a dict
class _MessagePayload(BaseModel):
    content: Optional[str] = None


class _ChoicePayload(BaseModel):
    message: Optional[_MessagePayload] = None


class _UsagePayload(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class _ModelOutputPayload(BaseModel):
    model: Optional[str] = None
    choices: Optional[list[_ChoicePayload]] = Field(
        default_factory=list
    )  # Corrected usage: List to list
    usage: Optional[_UsagePayload] = None

    class Config:
        extra = "allow"  # Allow other fields in the dict not defined in model # noqa


"""
NOTE: We use contextvars to store the current state of the callback, so it is thread-safe.
"""


# 1. Define a custom callback class that extends BaseCallback class
class LangFuseDSPYCallback(BaseCallback):  # noqa
    def __init__(self, signature: type[dspy_Signature]) -> None:
        super().__init__()
        # Use contextvars for per-call state
        self.current_system_prompt = contextvars.ContextVar[str](
            "current_system_prompt"
        )
        self.current_prompt = contextvars.ContextVar[str]("current_prompt")
        self.current_completion = contextvars.ContextVar[str]("current_completion")
        self.current_span = contextvars.ContextVar[Optional[StatefulGenerationClient]](
            "current_span"
        )
        self.model_name_at_span_creation = contextvars.ContextVar[Optional[str]](
            "model_name_at_span_creation"
        )
        self.input_field_values = contextvars.ContextVar[dict[str, Any]](
            "input_field_values"
        )
        # Initialize Langfuse client
        self.langfuse = Langfuse()
        self.input_field_names = signature.input_fields.keys()

    def on_module_start(  # noqa
        self,  # noqa
        call_id: str,  # noqa
        instance: Any,  # noqa
        inputs: dict[str, Any],
    ) -> None:
        extracted_args = inputs["kwargs"]
        input_field_values: dict[str, Any] = {}
        for input_field_name in self.input_field_names:
            if input_field_name in extracted_args:
                input_value = extracted_args[input_field_name]
                # Handle dspy.Image by extracting the data URI or URL
                if isinstance(input_value, dspy_Image) and hasattr(input_value, "url"):
                    input_field_values[input_field_name] = input_value.url
                else:
                    input_field_values[input_field_name] = input_value
        self.input_field_values.set(input_field_values)

    def on_module_end(  # noqa
        self,  # noqa
        call_id: str,  # noqa
        outputs: Optional[Any],
        exception: Optional[Exception] = None,  # noqa
    ) -> None:
        metadata = {
            "existing_trace_id": langfuse_context.get_current_trace_id(),
            "parent_observation_id": langfuse_context.get_current_observation_id(),
        }
        outputs_extracted = {}  # Default to empty dict
        if outputs is not None:
            try:
                outputs_extracted = {k: v for k, v in outputs.items()}
            except AttributeError:
                outputs_extracted = {"value": outputs}
            except Exception as e:
                outputs_extracted = {"error_extracting_module_output": str(e)}
        langfuse_context.update_current_observation(
            input=self.input_field_values.get(None) or {},
            output=outputs_extracted,
            metadata=metadata,
        )

    def on_lm_start(  # noqa
        self,  # noqa
        call_id: str,  # noqa
        instance: Any,
        inputs: dict[str, Any],
    ) -> None:
        # There is a double-trigger, so only count the first trigger.
        if self.current_span.get(None):
            return
        lm_instance = instance
        lm_dict = lm_instance.__dict__
        model_name = lm_dict.get("model")
        temperature = lm_dict.get("kwargs", {}).get("temperature")
        max_tokens = lm_dict.get("kwargs", {}).get("max_tokens")
        messages = inputs.get("messages")
        if messages is None:
            raise ValueError("Messages must be provided")
        if not messages or messages[0].get("role") != "system":
            raise ValueError("First message must be a system message")
        system_prompt = messages[0].get("content")
        if len(messages) < 2 or messages[1].get("role") != "user":
            raise ValueError("Second message must be a user message")
        user_input = messages[1].get("content")
        self.current_system_prompt.set(system_prompt)
        self.current_prompt.set(user_input)
        self.model_name_at_span_creation.set(model_name)
        trace_id = langfuse_context.get_current_trace_id()
        parent_observation_id = langfuse_context.get_current_observation_id()
        span_obj: Optional[StatefulGenerationClient] = None
        if trace_id:
            span_obj = self.langfuse.generation(  # type: ignore (Langfuse fails the type check in this function, grr...)
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

    def on_lm_end(  # noqa
        self,  # noqa
        call_id: str,  # noqa
        outputs: dict[str, Any] | list[Any] | None,
        exception: Optional[Exception] = None,
    ) -> None:
        completion_content: Optional[str] = None
        model_name: Optional[str] = self.model_name_at_span_creation.get(None)
        level: Literal["DEFAULT", "WARNING", "ERROR"] = "DEFAULT"
        status_message: Optional[str] = None

        prompt_tokens: Optional[int] = None
        completion_tokens: Optional[int] = None
        total_tokens: Optional[int] = None

        span = self.current_span.get(None)
        system_prompt: Optional[str] = self.current_system_prompt.get(None)
        prompt: Optional[str] = self.current_prompt.get(None)

        if exception:
            level = "ERROR"
            status_message = str(exception)
        elif outputs is None:
            level = "ERROR"
            status_message = (
                "LM call returned None outputs without an explicit exception."
            )
        elif isinstance(outputs, list):
            # Ensure it's a list of strings as expected for completion content from a list
            if (
                outputs
                and all(isinstance(item, str) for item in outputs)
                and outputs[0]
            ):
                completion_content = outputs[0]  # Taking the first string completion
            elif not outputs:
                level = "WARNING"
                status_message = "LM call returned an empty list as outputs."
            else:
                level = "ERROR"
                status_message = f"LM call returned a list, but it's not a list of strings or is empty in an unexpected way: {str(outputs)[:200]}"
        # If not exception, None, or list, it must be a dict based on the type hint
        else:  # This implies outputs is dict[str, Any]
            try:
                # Attempt to parse the dictionary using the Pydantic model
                parsed_output = _ModelOutputPayload.model_validate(
                    outputs
                )  # outputs is now known to be a dict

                if parsed_output.model:
                    model_name = (
                        parsed_output.model
                    )  # Override model_name if present in output

                # Extract completion content from choices
                if parsed_output.choices:
                    first_choice = (
                        parsed_output.choices[0] if parsed_output.choices else None
                    )
                    if first_choice and first_choice.message:
                        completion_content = first_choice.message.content

                if (
                    not completion_content and level == "DEFAULT"
                ):  # Only warn if no error yet and no content found
                    level = "WARNING"
                    status_message = "LM output (dict) did not contain expected choices[0].message.content structure."

                # Extract usage information
                if parsed_output.usage:
                    prompt_tokens = parsed_output.usage.prompt_tokens
                    completion_tokens = parsed_output.usage.completion_tokens
                    total_tokens = parsed_output.usage.total_tokens

            except ValidationError as e:
                level = "ERROR"
                status_message = f"Error validating LM output structure (dict using Pydantic): {e}. Output: {str(outputs)[:200]}"
            except (
                Exception
            ) as e:  # Catch any other unexpected errors during dict processing
                level = "ERROR"
                status_message = f"Unexpected error processing LM output (dict): {e}. Output: {str(outputs)[:200]}"

        # --- Usage and Cost Calculation ---
        can_calculate_usage = (
            completion_content is not None
            and system_prompt is not None
            and prompt is not None
            and model_name is not None
        )

        if can_calculate_usage:
            # Ensure types are concrete for calculations, falling back to empty strings if None (should not happen due to can_calculate_usage check)
            current_system_prompt: str = (
                system_prompt if system_prompt is not None else ""
            )
            current_prompt: str = prompt if prompt is not None else ""
            current_completion_content: str = (
                completion_content if completion_content is not None else ""
            )
            current_model_name: str = model_name if model_name is not None else ""

            try:
                final_prompt_tokens: int
                final_completion_tokens: int
                final_total_tokens: int

                if (
                    prompt_tokens is not None
                    and completion_tokens is not None
                    and total_tokens is not None
                ):
                    final_prompt_tokens = prompt_tokens
                    final_completion_tokens = completion_tokens
                    final_total_tokens = total_tokens
                else:
                    final_prompt_tokens = len(current_system_prompt + current_prompt)
                    final_completion_tokens = len(current_completion_content)
                    final_total_tokens = final_prompt_tokens + final_completion_tokens

                total_cost: Optional[float] = None  # Initialize to None
                try:
                    total_cost = completion_cost(
                        model=current_model_name,
                        prompt=current_system_prompt + current_prompt,
                        completion=current_completion_content,
                    )
                except Exception as cost_calc_exception:
                    log.warning(
                        f"litellm.completion_cost failed for model {current_model_name}: {cost_calc_exception}"
                    )
                    # total_cost remains None or you could set a default like 0.0
                    if level == "DEFAULT":
                        level = "WARNING"
                    status_message = (
                        status_message + "; " if status_message else ""
                    ) + f"Cost calculation failed: {cost_calc_exception}"

                if (
                    span and total_cost is not None
                ):  # Only update usage/cost if cost calculation was successful
                    usage_details_update = {
                        "input": final_prompt_tokens,
                        "output": final_completion_tokens,
                        "total": final_total_tokens,
                        # "cache_read_input_tokens": 0, # Optional: if you track this
                    }
                    cost_details_update = {
                        "input": (
                            (total_cost * (final_prompt_tokens / final_total_tokens))
                            if final_total_tokens
                            else 0.0
                        ),
                        "output": (
                            (
                                total_cost
                                * (final_completion_tokens / final_total_tokens)
                            )
                            if final_total_tokens
                            else 0.0
                        ),
                        "total": total_cost,
                        # "cache_read_input_tokens": 0.0, # Optional
                    }
                    span.update(  # type: ignore[call-arg] # Langfuse typing for update can be tricky
                        usage_details=usage_details_update,
                        cost_details=cost_details_update,
                    )
            except Exception as e:
                # This outer try-except catches errors in the token calculation logic itself
                log.warning(f"General failure in usage/cost block: {str(e)}")
                if level == "DEFAULT":
                    level = "WARNING"
                status_message = (
                    status_message + "; " if status_message else ""
                ) + f"Usage/cost processing error: {str(e)}"

        elif (
            level == "DEFAULT"
        ):  # Only log missing info if no other error/warning occurred
            missing_info_elements: list[str] = []
            if completion_content is None:
                missing_info_elements.append("completion content")
            if system_prompt is None:
                missing_info_elements.append("system prompt")
            if prompt is None:
                missing_info_elements.append("user prompt")
            if model_name is None:
                missing_info_elements.append("model name")

            if missing_info_elements:
                log.warning(
                    f"Missing required information for full usage/cost calculation: {', '.join(missing_info_elements)}"
                )
                # status_message = (status_message + "; " if status_message else "") + f"Missing info for cost calc: { ', '.join(missing_info_elements)}"

        # --- Finalize Span ---
        if span:
            end_args: dict[str, Any] = {
                "output": completion_content,
                "model": model_name,
                "level": level,
                "status_message": status_message,
            }
            # Langfuse client's `end` method handles None for these specific optional parameters.
            span.end(**end_args)  # type: ignore[call-arg] # Langfuse typing for end can be tricky
            self.current_span.set(None)

        if level == "DEFAULT" and completion_content is not None:
            self.current_completion.set(completion_content)
