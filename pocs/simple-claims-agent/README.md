# simple-claims-agent

A standalone Python command-line agent that reuses the Claim MCP server from
`langgraph-mcp-claims`.

It has two paths:

```text
command-line instruction
          |
          v
simple keyword router
     /             \
claims question   anything else
     |                   |
GPT + Claim MCP      GPT directly
     |
final answer
```

Claims-related instructions are given the three Claim MCP tools. OpenAI GPT
chooses the appropriate tool, the agent calls the existing MCP server, and GPT
turns the returned mock data into the final response. Non-claims instructions
never receive MCP tools and go directly to GPT.

## Setup

Prerequisites: Python 3.11+ and an OpenAI API key.

```powershell
cd C:\Users\ysati\yandagudita\work\ai-workspace\langraph-playground\simple-claims-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set `OPENAI_API_KEY` in `.env`. The key is never stored in source code, and
`.env` is ignored by Git.

## Run it

From the project directory with the virtual environment active:

```powershell
python main.py "What is the status of claim CLM1001?"
python main.py "What payment was made for claim CLM1001?"
python main.py "Explain recursion in simple terms."
```

You can also run it interactively:

```powershell
python main.py
```

The existing Claim MCP server is launched automatically as a local stdio
subprocess when a claims question needs it. A separate MCP server terminal is
not required.

If the shared MCP project is somewhere else, set its path before running:

```powershell
$env:CLAIMS_MCP_PROJECT = "C:\path\to\langgraph-mcp-claims"
python main.py "Show member MEM1001"
```

## How it works

- `main.py` collects the command-line instruction and starts the async agent.
- `is_claims_question` is a deliberately simple keyword router. It looks for
  words such as `claim`, `member`, `payment`, `CLM`, or `MEM`.
- Non-claims instructions call `ChatOpenAI` directly.
- Claims instructions discover the current MCP tool schemas and bind them to
  `ChatOpenAI` with LangChain.
- GPT emits a tool call when it needs claims data.
- The MCP client calls the existing `mcp_server.server` process over stdio.
- The tool result is placed in a `ToolMessage`, then sent back to GPT for the
  final natural-language answer.

This project does not use LangGraph; it is intentionally a smaller standalone
agent so the routing and MCP handoff are easy to follow. The neighboring
`langgraph-mcp-claims` project demonstrates the same MCP boundary coordinated
explicitly with a LangGraph `StateGraph`.

## Verify the local pieces

```powershell
python -m compileall agent.py main.py
python -c "from agent import is_claims_question; print(is_claims_question('status of CLM1001')); print(is_claims_question('explain recursion'))"
```

An end-to-end run requires a valid `OPENAI_API_KEY` because GPT performs both
the tool-selection and final-answer steps.
