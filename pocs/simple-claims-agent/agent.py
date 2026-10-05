"""A small command-line agent that routes claims questions through MCP."""

import json
import os
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# The agent reuses the Claim MCP project created beside this project.
DEFAULT_MCP_PROJECT = Path(__file__).resolve().parents[1] / "langgraph-mcp-claims"


def is_claims_question(instruction: str) -> bool:
    """Use a transparent, intentionally simple router for this demo.

    A production agent might use a classifier or another model, but keywords
    make the routing decision easy to inspect while learning the architecture.
    """
    text = instruction.lower()
    claims_terms = (
        "claim",
        "member",
        "payment",
        "insurance",
        "clm",
        "mem",
    )
    return any(term in text for term in claims_terms)


def _server_parameters() -> StdioServerParameters:
    """Describe how the MCP client should launch the shared Claim MCP server."""
    mcp_project = Path(os.getenv("CLAIMS_MCP_PROJECT", str(DEFAULT_MCP_PROJECT)))
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(mcp_project),
    )


async def discover_tools() -> list[dict[str, Any]]:
    """Discover current tool names and schemas from the MCP server."""
    async with stdio_client(_server_parameters()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "Claim lookup tool",
                        # MCP 2.x uses the Python attribute input_schema.
                        "parameters": tool.input_schema,
                    },
                }
                for tool in result.tools
            ]


async def call_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
    """Call one tool on the shared Claim MCP server and return readable text."""
    async with stdio_client(_server_parameters()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            if result.is_error:
                return json.dumps({"error": f"MCP tool {name} returned an error."})
            text_parts = [block.text for block in result.content if hasattr(block, "text")]
            return "\n".join(text_parts) or json.dumps(result.structured_content or {})


async def process_instruction(instruction: str) -> str:
    """Route one instruction to MCP-backed GPT or ordinary GPT."""
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Non-claims work never receives claims tools, so GPT simply answers it.
    if not is_claims_question(instruction):
        response = await model.ainvoke([HumanMessage(content=instruction)])
        return response.content

    # Claims work gets the live tool definitions from MCP. GPT chooses the
    # appropriate tool, so the router does not need to understand every query.
    messages = [HumanMessage(content=instruction)]
    response = await model.bind_tools(await discover_tools()).ainvoke(messages)
    messages.append(response)

    if not response.tool_calls:
        return response.content

    # Send each requested call through MCP, then give the results back to GPT
    # so it can compose the final answer instead of exposing raw JSON.
    for tool_call in response.tool_calls:
        result = await call_mcp_tool(tool_call["name"], tool_call["args"])
        messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    final_response = await model.ainvoke(messages)
    return final_response.content
