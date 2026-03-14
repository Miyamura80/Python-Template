"""
Temporary test script to debug Langfuse trace nesting.

Run with: uv run python scripts/test_langfuse_tracing.py
"""

import asyncio
import time
import dspy
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

from utils.llm.dspy_inference import DSPYInference
from utils.llm.dspy_langfuse import LangFuseDSPYCallback


class SimpleSignature(dspy.Signature):
    """A simple test signature."""

    message: str = dspy.InputField(desc="User message")
    response: str = dspy.OutputField(desc="Response")


def verify_trace_nesting(langfuse_client: Langfuse, trace_id: str, expected_name: str):
    """Verify that LLM generations are nested under the trace."""
    print(f"\nVerifying trace {trace_id}...")
    print(f"  Expected name: {expected_name}")
    print("  Check Langfuse dashboard: https://cloud.langfuse.com/")
    print(f"  Search for trace ID: {trace_id}")

    # Wait a bit for data to be available, then try to fetch
    time.sleep(5)

    try:
        # Fetch the trace
        trace = langfuse_client.fetch_trace(trace_id)
        print(f"  ✅ Trace found! Name: {trace.data.name}")

        # Fetch observations (generations) for this trace
        observations = langfuse_client.fetch_observations(trace_id=trace_id)
        print(f"  Observations count: {len(observations.data)}")

        for obs in observations.data:
            print(f"    - {obs.type}: {obs.name}")

        if len(observations.data) > 0:
            print("  ✅ LLM generations are nested under trace!")
            return True
        else:
            print("  ⚠️ No observations found yet (may need more time)")
            return False

    except Exception as e:
        print(f"  ⚠️ Trace not available yet: {e}")
        print("  (This is normal - traces take a few seconds to appear)")
        return False


async def test_explicit_trace_id():
    """Test passing explicit trace_id to DSPYInference."""
    print("\n=== Test 1: Explicit trace_id passed to DSPYInference ===")

    trace_name = "test-explicit-trace-email@example.com"
    langfuse_client = Langfuse()
    trace = langfuse_client.trace(name=trace_name)
    trace_id = trace.id
    print(f"Created trace with ID: {trace_id}")

    inference = DSPYInference(
        pred_signature=SimpleSignature,
        tools=[],
        observe=True,
        trace_id=trace_id,
    )

    result = await inference.run(message="Hello, what is 2+2?")
    print(f"Result: {result.response}")

    trace.update(output={"status": "completed"})
    langfuse_client.flush()

    # Verify the trace structure
    verify_trace_nesting(langfuse_client, trace_id, trace_name)


async def test_with_observe_decorator():
    """Test using @observe decorator - this should work."""
    print("\n=== Test 2: Using @observe decorator ===")

    @observe(name="test-observe-decorator-email@example.com")
    async def run_with_observe():
        trace_id = langfuse_context.get_current_trace_id()
        obs_id = langfuse_context.get_current_observation_id()
        print(f"Inside @observe: trace_id={trace_id}, observation_id={obs_id}")

        inference = DSPYInference(
            pred_signature=SimpleSignature,
            tools=[],
            observe=True,
            # Don't pass trace_id - let it pick up from langfuse_context
        )

        result = await inference.run(message="Hello, what is 3+3?")
        print(f"Result: {result.response}")
        return result

    await run_with_observe()
    print("Check Langfuse for trace named 'test-observe-decorator-email@example.com'")


async def test_callback_trace_context():
    """Test what the callback sees when we pass trace_id."""
    print("\n=== Test 3: Debug callback trace context ===")

    langfuse_client = Langfuse()
    trace = langfuse_client.trace(name="test-debug-callback-email@example.com")
    trace_id = trace.id
    print(f"Created trace with ID: {trace_id}")

    # Check what langfuse_context sees right now
    ctx_trace_id = langfuse_context.get_current_trace_id()
    ctx_obs_id = langfuse_context.get_current_observation_id()
    print(
        f"langfuse_context BEFORE inference: trace_id={ctx_trace_id}, obs_id={ctx_obs_id}"
    )

    # Create callback directly to inspect
    callback = LangFuseDSPYCallback(
        SimpleSignature,
        trace_id=trace_id,
        parent_observation_id=None,
    )
    print(f"Callback explicit trace_id: {callback._explicit_trace_id}")

    inference = DSPYInference(
        pred_signature=SimpleSignature,
        tools=[],
        observe=True,
        trace_id=trace_id,
    )
    if inference.callback:
        print(
            f"Inference callback explicit trace_id: {inference.callback._explicit_trace_id}"  # type: ignore[attr-defined]
        )

    result = await inference.run(message="Hello, what is 4+4?")
    print(f"Result: {result.response}")

    trace.update(output={"status": "completed"})
    langfuse_client.flush()
    print(f"Check Langfuse for trace: {trace_id}")


async def test_streaming_with_trace():
    """Test streaming with explicit trace_id."""
    print("\n=== Test 4: Streaming with explicit trace_id ===")

    trace_name = "test-streaming-email@example.com"
    langfuse_client = Langfuse()
    trace = langfuse_client.trace(name=trace_name)
    trace_id = trace.id
    print(f"Created trace with ID: {trace_id}")

    inference = DSPYInference(
        pred_signature=SimpleSignature,
        tools=[],
        observe=True,
        trace_id=trace_id,
    )

    chunks = []
    async for chunk in inference.run_streaming(
        stream_field="response",
        message="Count from 1 to 5",
    ):
        chunks.append(chunk)
        print(f"Chunk: {chunk}")

    full_response = "".join(chunks)
    print(f"Full response: {full_response}")

    trace.update(output={"status": "completed", "response": full_response})
    langfuse_client.flush()

    # Verify the trace structure
    verify_trace_nesting(langfuse_client, trace_id, trace_name)


async def test_agent_endpoint_pattern():
    """Test the exact pattern used in agent streaming endpoint."""
    print("\n=== Test 5: Agent Endpoint Pattern (streaming inside generator) ===")

    email = "test-user@example.com"
    trace_name = f"agent-stream-{email}"

    langfuse_client = Langfuse()
    trace = langfuse_client.trace(name=trace_name, user_id="test-user-123")
    trace_id = trace.id
    print(f"Created trace with ID: {trace_id}")
    print(f"Trace name: {trace_name}")

    async def stream_generator():
        """Mimics the agent endpoint's stream_generator."""
        inference = DSPYInference(
            pred_signature=SimpleSignature,
            tools=[],
            observe=True,
            trace_id=trace_id,
        )

        async for chunk in inference.run_streaming(
            stream_field="response",
            message="Say hello",
        ):
            yield chunk

    # Consume the generator (like FastAPI does with StreamingResponse)
    chunks = []
    async for chunk in stream_generator():
        chunks.append(chunk)
        print(f"Chunk: {repr(chunk)}")

    full_response = "".join(chunks)
    print(f"Full response: {full_response}")

    trace.update(output={"status": "completed", "response": full_response})
    langfuse_client.flush()

    # Verify
    verify_trace_nesting(langfuse_client, trace_id, trace_name)


async def main():
    print("=" * 60)
    print("Langfuse Trace Nesting Debug Script")
    print("=" * 60)

    # Focus on the most important test: agent endpoint pattern
    await test_agent_endpoint_pattern()

    print("\n" + "=" * 60)
    print("All tests completed. Check Langfuse dashboard for results.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
