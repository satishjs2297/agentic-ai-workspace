"""The state carried from node to node by LangGraph."""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ClaimsState(TypedDict):
    """State is the shared whiteboard for this graph.

    ``messages`` contains the conversation so far. ``add_messages`` tells
    LangGraph to append new messages instead of replacing the old list.
    """

    messages: Annotated[list[AnyMessage], add_messages]
