"""Streamlit UI for orchestrating the approval-aware recruitment graph.

The workflow logic remains in workflow.py. This module only translates browser
actions into graph invocations and renders graph state for the recruiter.
"""

import json
import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command

from workflow import build_graph


load_dotenv()


@st.cache_resource
def get_graph():
    """Create one compiled graph per Streamlit process.

    The graph includes an in-memory checkpointer. Each browser session gets its
    own thread ID below, so separate recruiters do not share workflow state.
    """
    return build_graph()


def initialize_session() -> None:
    """Create the UI session's graph pointer and workflow slots once."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "workflow_result" not in st.session_state:
        st.session_state.workflow_result = None
    if "request" not in st.session_state:
        st.session_state.request = ""


def graph_config() -> dict:
    """Return the stable thread ID used to pause and resume this workflow."""
    return {
        "configurable": {"thread_id": st.session_state.thread_id},
        "run_name": "recruitment_workflow_streamlit",
        "tags": ["recruitment", "human-in-the-loop", "streamlit"],
        "metadata": {"workflow": "agentic-recruitment", "entrypoint": "streamlit"},
    }


def pending_interrupt(result: dict) -> dict | None:
    """Extract the current human approval payload, if the graph is paused."""
    interrupts = result.get("__interrupt__") if result else None
    return interrupts[0].value if interrupts else None


def start_workflow(request: str) -> None:
    """Start the graph and save its result so reruns do not restart it."""
    st.session_state.request = request
    st.session_state.workflow_result = get_graph().invoke(
        {"request": request, "audit_log": []}, graph_config()
    )


def resume_workflow(action: str) -> None:
    """Resume the paused LangGraph thread from a button click."""
    st.session_state.workflow_result = get_graph().invoke(
        Command(resume={"action": action}), graph_config()
    )


def reset_workflow() -> None:
    """Start a clean browser-session workflow with a new thread ID."""
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.workflow_result = None
    st.session_state.request = ""


def render_approval(payload: dict) -> None:
    """Render a pending interrupt and map UI buttons to resume values."""
    st.warning(payload.get("question", "Human approval required"))
    st.caption(f"Phase: {payload.get('phase', 'approval')}")

    if "shortlist" in payload:
        st.subheader("Candidate shortlist")
        st.dataframe(payload["shortlist"], use_container_width=True)
    if "interview_plan" in payload:
        st.subheader("Interview plan")
        st.json(payload["interview_plan"])
    if "offer" in payload:
        st.subheader("Draft offer")
        st.json(payload["offer"])

    approve, reject = st.columns(2)
    with approve:
        if st.button("Approve", type="primary", use_container_width=True):
            resume_workflow("approve")
            st.rerun()
    with reject:
        if st.button("Reject", use_container_width=True):
            resume_workflow("reject")
            st.rerun()


def render_result(result: dict) -> None:
    """Render final status and the audit trail after a workflow decision."""
    status = result.get("status", "in progress")
    if status == "completed":
        st.success(result.get("final_message", "Workflow completed."))
    elif status == "stopped":
        st.error(result.get("final_message", "Workflow stopped."))
    else:
        st.info(result.get("final_message", f"Workflow status: {status}"))

    with st.expander("Audit log", expanded=True):
        for entry in result.get("audit_log", []):
            st.write(f"- {entry}")

    with st.expander("Workflow state"):
        # Remove LangGraph's interrupt object before JSON display.
        safe_result = {key: value for key, value in result.items() if key != "__interrupt__"}
        st.code(json.dumps(safe_result, indent=2, default=str), language="json")


def main() -> None:
    st.set_page_config(page_title="Recruitment Workflow", page_icon="👥", layout="wide")
    initialize_session()

    st.title("👥 Agentic Recruitment Workflow")
    st.write("Use LangGraph agents to prepare hiring actions, with human approval before each consequential phase.")

    with st.sidebar:
        st.header("Workflow phases")
        st.markdown("""
        1. Intake
        2. Source candidates
        3. Screen candidates
        4. Approve shortlist
        5. Approve interviews
        6. Approve offer
        7. Finalize
        """)
        st.caption(f"Thread: {st.session_state.thread_id}")
        langsmith_key = os.getenv("LANGSMITH_API_KEY", "")
        tracing_enabled = langsmith_key and not langsmith_key.startswith("your-") and os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
        if tracing_enabled:
            st.success("LangSmith tracing enabled")
        else:
            st.info("LangSmith tracing disabled")
        if st.button("Start a new workflow", use_container_width=True):
            reset_workflow()
            st.rerun()

    result = st.session_state.workflow_result
    if result is None:
        with st.form("recruitment_request"):
            request = st.text_area(
                "What role are you hiring for?",
                placeholder="Hire a Python engineer to build internal AI workflows",
                height=120,
            )
            submitted = st.form_submit_button("Start recruitment workflow", type="primary")
        if submitted:
            if request.strip():
                start_workflow(request.strip())
                st.rerun()
            else:
                st.error("Please describe the hiring request.")
        return

    payload = pending_interrupt(result)
    if payload:
        render_approval(payload)
    else:
        render_result(result)


if __name__ == "__main__":
    main()
