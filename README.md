# agentic-ai-workspace

This repository contains small educational proofs of concept for agentic AI
workflows built with Python, LangChain, LangGraph, CrewAI, MCP, and Streamlit.

## Projects

- [`pocs/langgraph-mcp-claims`](pocs/langgraph-mcp-claims): LangGraph + OpenAI
  + official MCP client/server claims example.
- [`pocs/simple-claims-agent`](pocs/simple-claims-agent): command-line agent
  that routes claims prompts through the Claim MCP server and other prompts to
  the LLM.
- [`pocs/crewai-claims-agent`](pocs/crewai-claims-agent): CrewAI version of the
  claims agent using the current MCP client boundary.
- [`pocs/agentic-recruitment-langgraph`](pocs/agentic-recruitment-langgraph):
  approval-aware recruitment workflow with CLI and Streamlit UI, LangGraph
  interrupts, and optional LangSmith tracing.

Each POC has its own README and `requirements.txt`. Create a separate virtual
environment inside the POC you want to run; environments and installed
packages are intentionally ignored by Git.

## What is committed

The repository commits source code, package markers, README documentation,
dependency manifests, safe `.env.example` templates, and project-level Git
ignore files. It does not commit API keys, real `.env` files, virtual
environments, installed packages, caches, compiled Python files, binaries,
logs, databases, or IDE state.
