from dspy.utils.callback import BaseCallback
from langfuse.decorators import langfuse_context
from langfuse import Langfuse
from litellm import completion_cost
from langfuse.media import LangfuseMedia
from typing import Optional
import dspy


# 1. Define a custom callback class that extends BaseCallback class
class LangFuseDSPYCallback(BaseCallback):
    def __init__(self, signature: dspy.Signature):
        super().__init__()
        self.current_system_prompt = None
        self.current_prompt = None
        self.current_completion = None
        # Initialize Langfuse client
        self.langfuse = Langfuse()
        self.current_span = None
        self.model_name_at_span_creation = None  # Added for robust model name handling

        self.input_field_names = signature.input_fields.keys()
        self.input_field_values = {}

        for input_field_name, input_field in signature.input_fields.items():
            if (
                input_field.annotation == Optional[dspy.Image]
                or input_field.annotation == dspy.Image
            ):
                pass  # TODO: We need to handle this.

    def on_module_start(self, call_id, *args, **kwargs):
        inputs = kwargs.get("inputs")
        extracted_args = inputs["kwargs"]

        for input_field_name in self.input_field_names:
            if input_field_name in extracted_args:
                self.input_field_values[input_field_name] = extracted_args[
                    input_field_name
                ]

    def on_module_end(self, call_id, outputs, exception):
        metadata = {
            "existing_trace_id": langfuse_context.get_current_trace_id(),
            "parent_observation_id": langfuse_context.get_current_observation_id(),
        }
        outputs_extracted = {}  # Default to empty dict

        if outputs is not None:
            try:
                # dspy.Prediction objects (common for module outputs) are dict-like
                outputs_extracted = {k: v for k, v in outputs.items()}
            except AttributeError:
                # If 'outputs' is not None but doesn't have .items() (e.g., a string, int)
                # Store it as a simple value in the dict for Langfuse.
                outputs_extracted = {"value": outputs}
            except Exception as e:
                # Catch any other unexpected error during extraction
                outputs_extracted = {"error_extracting_module_output": str(e)}
        # If 'outputs' was None, outputs_extracted remains {}

        langfuse_context.update_current_observation(
            input=self.input_field_values, output=outputs_extracted, metadata=metadata
        )

    def on_lm_start(self, call_id, *args, **kwargs):
        # There is a double-trigger, so only count the first trigger.
        if self.current_span:
            return

        # Everything related to the LM instance
        lm_instance = kwargs.get("instance")
        lm_dict = lm_instance.__dict__
        model_name = lm_dict.get("model")
        temperature = lm_dict.get("kwargs", {}).get("temperature")
        max_tokens = lm_dict.get("kwargs", {}).get("max_tokens")

        # Everything related to the input
        inputs = kwargs.get("inputs")
        messages = inputs.get("messages")

        # Extract prompt from kwargs
        assert messages[0].get("role") == "system"
        system_prompt = messages[0].get("content")
        assert messages[1].get("role") == "user"
        user_input = messages[1].get("content")

        self.current_system_prompt = system_prompt
        self.current_prompt = user_input

        # Store model_name at span creation time
        self.model_name_at_span_creation = model_name

        # Create a new generation using the Langfuse client
        trace_id = langfuse_context.get_current_trace_id()
        parent_observation_id = langfuse_context.get_current_observation_id()
        if trace_id:
            self.current_span = self.langfuse.generation(
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

    def on_lm_end(self, call_id, outputs, exception):
        completion_content = None
        model_name_for_span = None
        usage_for_span = None
        cost_for_span = None
        level = "DEFAULT"
        status_message = None

        # Use the model name stored at span creation as the primary source
        if self.current_span:
            model_name_for_span = self.model_name_at_span_creation

        if exception:
            level = "ERROR"
            status_message = str(exception)
            # model_name_for_span remains as set from model_name_at_span_creation
        elif outputs is None:
            level = "ERROR"
            status_message = (
                "LM call returned None outputs without an explicit exception."
            )
            # model_name_for_span remains as set from model_name_at_span_creation
        elif isinstance(outputs, list):
            if outputs:
                completion_content = outputs[
                    0
                ]  # Assuming the first element is the completion
                # For list outputs, model_name_for_span (from creation) is used.
            else:
                level = "WARNING"
                status_message = "LM call returned an empty list as outputs."
            # model_name_for_span remains as set from model_name_at_span_creation
        else:
            # This is for single, non-list, non-None, non-exception outputs
            try:
                # Attempt to get a more definitive model name from the LM output if available
                if hasattr(outputs, "model") and outputs.model is not None:
                    model_name_for_span = (
                        outputs.model
                    )  # Override if available and not None
                # If outputs.model is None or not present, model_name_for_span (from creation) is used.

                if (
                    outputs.choices
                    and outputs.choices[0]
                    and outputs.choices[0].message
                ):
                    completion_content = outputs.choices[0].message.content
                else:
                    level = "WARNING"
                    status_message = "LM output structure did not contain expected choices or message."

                if (
                    completion_content
                    and self.current_system_prompt is not None
                    and self.current_prompt is not None
                ):
                    try:
                        total_cost = completion_cost(
                            model=model_name_for_span,
                            prompt=self.current_system_prompt + self.current_prompt,
                            completion=completion_content,
                        )
                        cost_for_span = {"total": total_cost}

                        prompt_len = len(
                            self.current_system_prompt + self.current_prompt
                        )
                        completion_len = len(completion_content)
                        usage_for_span = {
                            "prompt_tokens": prompt_len,
                            "completion_tokens": completion_len,
                            "total_tokens": prompt_len + completion_len,
                        }
                    except Exception as e:
                        # Silently ignore cost/usage calculation errors for now, or log as warning
                        pass  # Or log.warning(f"Could not calculate cost/usage: {e}")
                else:
                    if not completion_content:
                        status_message = (
                            status_message
                            or "Completion content was empty or not found."
                        )
                    # Not enough info for cost/usage if prompts or completion are None

            except AttributeError as e:
                level = "ERROR"
                status_message = f"Error processing LM output structure: {e}. Output: {str(outputs)[:200]}"
            except Exception as e:  # Catch any other unexpected error
                level = "ERROR"
                status_message = f"Unexpected error processing LM output: {e}. Output: {str(outputs)[:200]}"

        # End the generation span
        if self.current_span:
            end_args = {
                "output": completion_content,
                "model": model_name_for_span,
                "level": level,
                "status_message": status_message,
            }
            if usage_for_span:
                end_args["usage"] = usage_for_span
            if cost_for_span:
                end_args["cost"] = cost_for_span

            final_end_args = {
                k: v
                for k, v in end_args.items()
                if v is not None or k in ["output", "model", "level", "status_message"]
            }

            self.current_span.end(**final_end_args)
            self.current_span = None

        if level == "OK" and completion_content is not None:
            self.current_generation = completion_content
        # else: self.current_generation might remain from a previous successful call, or be None.
        # Consider if self.current_generation should be explicitly set to None on error.
        # For now, it's only updated on success.
