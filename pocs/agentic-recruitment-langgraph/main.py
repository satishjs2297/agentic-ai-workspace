"""Command-line runner for the approval-aware recruitment workflow."""

import json
import os
import sys
import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from workflow import build_graph


def _show_interrupt(payload: dict) -> dict:
    """Display a pending approval and collect a deliberately small decision."""
    print("\n=== HUMAN APPROVAL REQUIRED ===")
    print(json.dumps(payload, indent=2))
    answer = input("Type approve or reject: ").strip().lower()
    while answer not in {"approve", "reject"}:
        answer = input("Please type approve or reject: ").strip().lower()
    return {"action": answer}


def main() -> None:
    load_dotenv()
    request = " ".join(sys.argv[1:]).strip()
    if not request:
        request = input("Describe the role you want to recruit for: ").strip()
    if not request:
        raise SystemExit("A hiring request is required.")

    graph = build_graph()
    config = {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "run_name": "recruitment_workflow_cli",
        "tags": ["recruitment", "human-in-the-loop", "cli"],
        "metadata": {"workflow": "agentic-recruitment", "entrypoint": "cli"},
    }
    result = graph.invoke({"request": request, "audit_log": []}, config)

    # Each interrupt pauses the same graph thread. Command(resume=...) feeds
    # the human decision back to the exact interrupt that paused execution.
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        result = graph.invoke(Command(resume=_show_interrupt(payload)), config)

    print("\n=== RESULT ===")
    print(result.get("final_message", "Workflow ended without a final message."))
    print("\n=== AUDIT LOG ===")
    for entry in result.get("audit_log", []):
        print(f"- {entry}")


if __name__ == "__main__":
    main()
