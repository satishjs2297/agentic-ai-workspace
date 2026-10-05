# langgraph-mcp-claims

A small educational Python 3.11+ project showing this request path:

```text
User -> LangGraph -> OpenAI GPT -> MCP client -> MCP server
                                      |              |
                                      |        mock claims data
                                      v              |
                         LangGraph <- tool result -+
                             |
                         GPT -> response
```

The example intentionally uses in-memory dictionaries. It has no database,
web server, authentication, container, or production infrastructure.

## Prerequisites

- Python 3.11 or newer
- An OpenAI API key
- Windows PowerShell (commands below assume PowerShell)

## Virtual-environment setup

From the project directory:

```powershell
cd C:\Users\ysati\yandagudita\work\ai-workspace\langraph-playground\langgraph-mcp-claims
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process
Bypass` for the current terminal, then activate again.

## `.env` configuration

Copy the example and edit it with your key:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `OPENAI_API_KEY=...`. The real `.env` is ignored by Git; never commit the
key. The application loads it with `python-dotenv`.

## Start the MCP server

The server uses the official MCP Python SDK and stdio transport. In a
dedicated PowerShell window:

```powershell
cd C:\Users\ysati\yandagudita\work\ai-workspace\langraph-playground\langgraph-mcp-claims
.\.venv\Scripts\Activate.ps1
python -m mcp_server.server
```

Stdio servers normally appear to wait silently because they communicate over
stdin/stdout. The application also launches this server automatically for each
discovery/tool call, so a separate server window is optional for normal use.

## Run the LangGraph application

In another PowerShell window:

```powershell
cd C:\Users\ysati\yandagudita\work\ai-workspace\langgraph-playground\langgraph-mcp-claims
.\.venv\Scripts\Activate.ps1
python main.py
```

Try:

- `What is the status of claim CLM1001?`
- `What payment was made for claim CLM1001?`
- `Show me the member information for member MEM1001.`

## How the request flows

1. `main.py` accepts a natural-language question and seeds `ClaimsState` with
   a `HumanMessage`.
2. The first `model` node uses `ChatOpenAI` from `langchain-openai`.
3. The node discovers MCP tool names and JSON schemas, then uses
   `model.bind_tools(...)`. GPT can answer directly or emit a tool call.
4. A LangGraph conditional edge inspects the AI message. Tool calls route to
   `mcp_tools`; no tool call routes to `END`.
5. `mcp_tools` uses the official MCP client (`ClientSession` plus stdio
   transport) to start/connect to `mcp_server.server` and call the requested
   tool.
6. The MCP result becomes a `ToolMessage` with the same `tool_call_id`.
7. The edge from `mcp_tools` returns to `model`, so GPT sees the tool result
   and writes the final natural-language response.

## LangGraph vs LangChain vs MCP

- **LangGraph** is the workflow/orchestration layer. `ClaimsState` is shared
  state; nodes are Python functions; edges describe movement; the conditional
  edge decides whether to call tools; `compile()` produces an executable graph.
- **LangChain** provides the message types and model abstraction. Here,
  `ChatOpenAI` is the LangChain integration for the OpenAI API, and
  `bind_tools` formats tool schemas for the chat model.
- **MCP** is the protocol boundary between an AI application and external
  tools/data. The server exposes `get_claim`, `get_member`, and
  `get_claim_payment`; the client discovers and calls them. The MCP server does
  not know about LangGraph, and LangGraph does not contain the claims lookup
  logic.

## Files explained

- `.env.example`: safe placeholder for the required environment variable.
- `.gitignore`: prevents `.env`, virtual-environment files, and Python cache
  files from being committed.
- `requirements.txt`: only the LangGraph, LangChain/OpenAI, MCP SDK, and dotenv
  packages needed by this example.
- `main.py`: loads configuration, accepts a question, and runs the graph.
- `graph/state.py`: declares the message state and append behavior.
- `graph/nodes.py`: contains the model node, MCP client helpers, tool node, and
  conditional routing function.
- `graph/workflow.py`: explicitly creates nodes, edges, conditional edges, and
  compiles the `StateGraph`.
- `mcp_server/server.py`: defines the in-memory mock data and three MCP tools.

## Verification

Useful checks from the project directory:

```powershell
python -m compileall graph mcp_server main.py
python -c "from mcp.server import MCPServer; from mcp import ClientSession; print('current MCP client/server imports work')"
python -c "from graph.workflow import build_graph; print(build_graph())"
```

The first check validates Python syntax; the second imports the MCP server and
confirms its three tools; the third confirms LangGraph can compile. A real
end-to-end answer additionally requires a valid `OPENAI_API_KEY`, because it
calls OpenAI.
