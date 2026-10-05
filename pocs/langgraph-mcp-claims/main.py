"""Command-line entry point for the LangGraph + MCP claims example."""

import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from graph.workflow import build_graph


async def answer_question(question: str) -> str:
    """Run one question through the compiled LangGraph."""
    result = await build_graph().ainvoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].content


def main() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is missing. Copy .env.example to .env and add your key.")
    question = input("Ask a claims question (or press Ctrl+C to quit): ")
    print("\nAnswer:\n" + asyncio.run(answer_question(question)))


if __name__ == "__main__":
    main()
