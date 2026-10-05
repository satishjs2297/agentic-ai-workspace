# agentic-recruitment-langgraph

An educational, approval-aware recruitment workflow built with LangGraph.
It models a multi-agent recruiting process while keeping data in memory and
making every consequential phase visible to a human.

## Workflow phases

```text
Hiring request
      |
      v
Intake agent -> Source candidates -> Screen candidates
                                      |
                         HUMAN: approve shortlist
                                      |
                         Interview planning agent
                                      |
                         HUMAN: approve interviews
                                      |
                              Offer agent drafts offer
                                      |
                         HUMAN: approve offer release
                                      |
                                  Finalize
```

The three approval gates are intentional: a system may assist with sourcing,
scoring, scheduling, and drafting, but a person remains responsible for
shortlisting, advancing candidates, and approving an offer.

## Project files

- `state.py` defines the shared recruitment case file.
- `workflow.py` defines the specialized agent nodes, edges, conditional
  routing, interrupts, mock candidate pool, and graph compilation.
- `main.py` runs the workflow from PowerShell and collects human approvals.
- `streamlit_app.py` provides the browser UI for starting workflows, reviewing
  approval payloads, and resuming the same LangGraph thread.
- `.env.example` documents the optional OpenAI key.
- `requirements.txt` contains LangGraph, LangChain/OpenAI, and dotenv.

## Setup in Windows PowerShell

Python 3.11+ is required. OpenAI is optional: without a key, the intake and
offer phases use deterministic educational fallbacks; with a key, the intake
brief is drafted by `gpt-4o-mini`.

```powershell
cd C:\Users\ysati\yandagudita\work\ai-workspace\langraph-playground\agentic-recruitment-langgraph
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

If using OpenAI, set `OPENAI_API_KEY` in `.env`. Never commit `.env`.

## Add LangSmith tracing

LangSmith tracing is optional. Add these values to `.env`:

```dotenv
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=agentic-recruitment-langgraph
```

Run the CLI or Streamlit UI normally. LangChain and LangGraph will send the
workflow trace to that LangSmith project. The trace includes the graph run,
node executions, model calls when an API key is configured, state transitions,
and pauses/resumptions around human approval. The CLI and UI use different
tags (`cli` and `streamlit`) so they can be filtered separately.

Tracing stays disabled when `LANGSMITH_API_KEY` is absent, so local testing does
not require a LangSmith account.

## Run the workflow

```powershell
python main.py "Hire a Python engineer to build internal AI workflows"
```

At each approval pause, review the JSON payload and type `approve` or
`reject`. Rejection stops the workflow and is recorded in the audit log.

## Run the Streamlit UI

The UI is the recommended way to orchestrate the workflow interactively:

```powershell
streamlit run streamlit_app.py
```

Open the local URL shown by Streamlit. Enter a hiring request, click **Start
recruitment workflow**, and use the **Approve** or **Reject** buttons at each
human gate. The UI keeps the LangGraph `thread_id` in the Streamlit session so
button clicks resume the paused workflow instead of starting a new one.

This demo uses `InMemorySaver`, which is suitable for local testing. Use a
durable LangGraph checkpointer before deploying the UI for multiple recruiters
or across process restarts.

## How human approval works

LangGraph's `interrupt()` pauses a running node and returns a JSON-serializable
approval payload to the caller. The graph is compiled with an in-memory
checkpointer and a `thread_id`, so the paused workflow can resume later with
`Command(resume={"action": "approve"})`. In production, replace
`InMemorySaver` with a durable checkpointer and persist the thread ID.

## Why these agents are separate

Each phase is a separate graph node with one responsibility:

- Intake creates a role brief.
- Sourcing finds candidates.
- Screening scores candidates.
- Interview planning proposes interview rounds.
- Offer drafting prepares, but does not send, an offer.
- Finalization summarizes the approved outcome.

This separation makes it possible to replace a deterministic node with an LLM,
an ATS connector, an MCP tool, or a policy service without redesigning the
entire workflow. The human approval nodes are the safety boundary around
decisions that affect people.

## Verification

```powershell
python -m compileall state.py workflow.py main.py
python -c "from workflow import build_graph; print(build_graph())"
```

The workflow can be exercised without an API key because the sample dataset,
screening rubric, and approval loop are local. Any OpenAI-assisted intake call
requires a valid API key.
