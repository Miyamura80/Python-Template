import asyncio
import dspy
from googlesearch import search
from utils.llm.dspy_inference import DSPYInference
from common import global_config
from loguru import logger as log
from src.utils.logging_config import setup_logging

# Set up logging at the start of your file
setup_logging()

class QuestionAnswer(dspy.Signature):
    """Answer a question, optionally using web search."""
    question: str = dspy.InputField()
    response: str = dspy.OutputField()

QUESTION = "What is the projected future demand for high bandwidth memory?"

def search_web(query: str) -> str:
    """Searches the web for a given query."""
    log.info(f"Searching web for: {query}")
    try:
        search_results = search(query, num_results=3)
        return str(list(search_results))
    except Exception as e:
        log.error(f"Error during web search: {e}")
        return "Web search failed."

async def main():
    """
    Main function to run the DSPy inference modules.
    """
    # 2022 Era ChatGPT, no up-to-date info
    log.info("Running predictor without web search...")
    predictor = DSPYInference(QuestionAnswer)
    response_no_search = await predictor.run(question=QUESTION)
    log.info(f"Response without web search: {response_no_search.response}")

    # 2023 Era ChatGPT, with web search
    log.info("Running ReAct agent with web search...")
    web_search_predictor = DSPYInference(QuestionAnswer, tools=[search_web])
    response_with_search = await web_search_predictor.run(question=QUESTION)
    log.info(f"Response with web search: {response_with_search.response}")

if __name__ == "__main__":
    asyncio.run(main())