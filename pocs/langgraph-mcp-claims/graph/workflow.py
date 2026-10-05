"""Explicit StateGraph definition: nodes, edges, conditional routing, compile."""

from langgraph.graph import END, START, StateGraph

from .nodes import call_mcp_tools, call_model, route_after_model
from .state import ClaimsState


def build_graph():
    """Build and compile the educational workflow."""
    builder = StateGraph(ClaimsState)
    # Nodes are functions that receive shared state and return state updates.
    builder.add_node("model", call_model)
    builder.add_node("mcp_tools", call_mcp_tools)
    # Start at GPT; after MCP returns, loop back to GPT for the final answer.
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route_after_model, {"mcp_tools": "mcp_tools", "finish": END})
    builder.add_edge("mcp_tools", "model")
    # Compilation validates the graph and returns the executable application.
    return builder.compile()
