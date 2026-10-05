# crewai-claims-agent

A small standalone CrewAI project that uses the existing Claim MCP server from
`langgraph-mcp-claims`.

```text
PowerShell instruction
          |
          v
claims keyword router
     /              \
claims prompt      other prompt
     |                   |
CrewAI agent        CrewAI agent
 + Claim MCP tools  without MCP tools
     |
Claim MCP server -> mock claims data
     |
final CrewAI answer
```

## What it does

- Claims prompts are given the Claim MCP tools:
  `get_claim`, `get_member`, and `get_claim_payment`.
- CrewAI's agent decides which MCP tool to use and uses its result in the
  answer.
- Non-claims prompts run through a normal CrewAI agent without claims tools.
- The MCP server is launched automatically over local stdio by the official
  current MCP Python client.

The routing rule is intentionally simple and visible in `agent.py`: it checks
for terms such as `claim`, `member`, `payment`, `CLM`, or `MEM`. This keeps the
example easy to understand; a production router could use a classifier.

## Setup in Windows PowerShell

Prerequisites: Python 3.11+ and an OpenAI API key.

If an earlier setup attempt failed while installing `crewai-tools[mcp]`,
recreate the environment first; this corrected version does not use that
incompatible adapter package.

```powershell
cd C:\Users\ysati\yandagudita\work\ai-workspace\langraph-playground\crewai-claims-agent
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set `OPENAI_API_KEY` in `.env`. The file is ignored by Git.

## Run it

```powershell
python main.py "What is the status of claim CLM1001?"
python main.py "What payment was made for claim CLM1001?"
python main.py "Explain recursion in simple terms."
```

Or run without arguments and type an instruction interactively:

```powershell
python main.py
```

If the existing Claim MCP project is in another location, configure it before
running:

```powershell
$env:CLAIMS_MCP_PROJECT = "C:\path\to\langgraph-mcp-claims"
python main.py "Show member MEM1001"
```

## How CrewAI and MCP connect

`agent.py` defines three small CrewAI `BaseTool` wrappers. Their `_run`
methods call the official current MCP Python client (`ClientSession` and
`stdio_client`) and launch the existing Claim MCP server. This keeps the
example compatible with the current MCP 2.x API while making the MCP boundary
visible in the code.

The example disables CrewAI/OpenTelemetry tracing by default because it is a
local educational program and does not need to send telemetry anywhere.

CrewAI owns the agent, task, crew, and execution. MCP owns the tool boundary
and mock claims data. OpenAI is the language model used by the CrewAI agent.

## Verify the local pieces

```powershell
python -m compileall agent.py main.py
python -c "from agent import is_claims_question; print(is_claims_question('status of CLM1001')); print(is_claims_question('explain recursion'))"
```

An end-to-end run requires `OPENAI_API_KEY` because CrewAI calls OpenAI for
both tool selection and response generation.
