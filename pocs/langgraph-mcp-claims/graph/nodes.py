"""LangGraph nodes and the official MCP client connection."""

import json
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def _discover_mcp_tools() -> list[dict[str, Any]]:
    """Discover the server's current tool schemas through MCP."""
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], cwd=str(PROJECT_ROOT))
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [{
                "type": "function",
                # MCP 2.x uses Pythonic ``input_schema``. Older examples often
                # show the wire-format name ``inputSchema`` instead.
                "function": {"name": tool.name, "description": tool.description or "MCP claims lookup tool", "parameters": tool.input_schema},
            } for tool in result.tools]


async def _call_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
    """Call one MCP server tool and convert its result into model-readable text."""
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], cwd=str(PROJECT_ROOT))
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            if result.is_error:
                return json.dumps({"error": f"MCP tool {name} returned an error."})
            text_parts = [block.text for block in result.content if hasattr(block, "text")]
            return "\n".join(text_parts) or json.dumps(result.structured_content or {})


async def call_model(state: dict[str, Any]) -> dict[str, list[AIMessage]]:
    """Model node: GPT answers or requests an MCP tool call.

    LangGraph owns orchestration; LangChain supplies the model wrapper.
    Binding the MCP-discovered schemas teaches GPT the available tools. GPT's
    AIMessage may then contain tool_calls instead of a final answer.
    """
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = await model.bind_tools(await _discover_mcp_tools()).ainvoke(state["messages"])
    return {"messages": [response]}


def route_after_model(state: dict[str, Any]) -> str:
    """Conditional edge: tool calls go to MCP; otherwise the graph finishes."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "mcp_tools"
    return "finish"


async def call_mcp_tools(state: dict[str, Any]) -> dict[str, list[ToolMessage]]:
    """Tool node: execute GPT's requested tools through the MCP client.

    Each result becomes a ToolMessage with the matching tool_call_id. The next
    model node sees that message and can write a grounded final response.
    """
    last_message = state["messages"][-1]
    messages = []
    for tool_call in last_message.tool_calls:
        result = await _call_mcp_tool(tool_call["name"], tool_call["args"])
        messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
    return {"messages": messages}
