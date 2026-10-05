"""The agentic recruitment workflow and its human approval gates."""

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from state import RecruitmentState


# LangChain/LangGraph automatically emit traces when these environment
# variables are present. Both CLI and Streamlit use this configuration.
load_dotenv()
langsmith_key = os.getenv("LANGSMITH_API_KEY", "")
if langsmith_key and not langsmith_key.startswith("your-"):
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "agentic-recruitment-langgraph")


MOCK_CANDIDATES = [
    {
        "candidate_id": "CAND-001",
        "name": "Jordan Patel",
        "skills": ["Python", "LangGraph", "APIs"],
        "years_experience": 5,
        "location": "Remote",
    },
    {
        "candidate_id": "CAND-002",
        "name": "Taylor Morgan",
        "skills": ["Python", "FastAPI", "AWS"],
        "years_experience": 4,
        "location": "New York",
    },
    {
        "candidate_id": "CAND-003",
        "name": "Casey Rivera",
        "skills": ["JavaScript", "React", "Node.js"],
        "years_experience": 3,
        "location": "Remote",
    },
]


def _llm() -> ChatOpenAI | None:
    """Return GPT when configured, while keeping the demo runnable offline."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def intake_agent(state: RecruitmentState) -> dict:
    """Agent 1: turn the request into a simple job brief.

    This is a separate node so an eventual production system can give intake
    its own prompt, policy, and tools without coupling it to screening.
    """
    model = _llm()
    if model:
        response = model.invoke(
            "Extract a concise role title and hiring brief from this request. "
            "Return plain text with the role title on the first line.\n\n"
            + state["request"]
        )
        text = str(response.content)
        role = text.splitlines()[0].strip() or "Software Engineer"
    else:
        text = "Software Engineer\nBuild and maintain Python services and AI workflows."
        role = "Software Engineer"
    return {"role": role, "job_summary": text, "audit_log": ["Intake agent created the job brief."]}


def sourcing_agent(state: RecruitmentState) -> dict:
    """Agent 2: source candidates from the demo in-memory candidate pool."""
    # Replace this list with an ATS, job board, or MCP search tool later.
    candidates = list(MOCK_CANDIDATES)
    return {
        "candidates": candidates,
        "audit_log": [f"Sourcing agent found {len(candidates)} mock candidates."],
    }


def screening_agent(state: RecruitmentState) -> dict:
    """Agent 3: score candidates against the role using explainable rules.

    The score is intentionally deterministic for learning and testing. A
    production version could combine structured rubrics with an LLM, while
    keeping the human gate before any consequential decision.
    """
    scored = []
    for candidate in state["candidates"]:
        skills = {skill.lower() for skill in candidate["skills"]}
        score = 50 + min(candidate["years_experience"] * 5, 25)
        if "python" in skills:
            score += 15
        if "langgraph" in skills or "apis" in skills:
            score += 10
        scored.append({**candidate, "screening_score": min(score, 100)})
    shortlist = sorted(scored, key=lambda item: item["screening_score"], reverse=True)[:2]
    return {
        "shortlist": shortlist,
        "audit_log": ["Screening agent scored candidates and prepared a shortlist."],
    }


def shortlist_approval(state: RecruitmentState) -> dict:
    """Human gate 1: require approval before advancing candidates."""
    decision = interrupt(
        {
            "phase": "shortlist_approval",
            "question": "Approve this candidate shortlist for interviews?",
            "shortlist": state["shortlist"],
            "allowed_actions": ["approve", "reject"],
        }
    )
    action = str(decision.get("action", "reject")).lower() if isinstance(decision, dict) else str(decision).lower()
    if action == "approve":
        return {"status": "shortlist_approved", "approvals": {"shortlist": "approved"}, "audit_log": ["Human approved the shortlist."]}
    return {"status": "stopped", "approvals": {"shortlist": "rejected"}, "audit_log": ["Human rejected the shortlist."]}


def route_after_shortlist(state: RecruitmentState) -> Literal["interviews", "stop"]:
    return "interviews" if state.get("status") == "shortlist_approved" else "stop"


def interview_agent(state: RecruitmentState) -> dict:
    """Agent 4: create a proposed interview plan for each approved candidate."""
    plan = {
        "rounds": ["Technical conversation", "Hiring manager conversation"],
        "candidates": [
            {"candidate_id": candidate["candidate_id"], "proposed_rounds": 2}
            for candidate in state["shortlist"]
        ],
    }
    return {"interview_plan": plan, "audit_log": ["Interview agent proposed interview rounds."]}


def interview_approval(state: RecruitmentState) -> dict:
    """Human gate 2: approve interviews before invitations are sent."""
    decision = interrupt(
        {
            "phase": "interview_approval",
            "question": "Approve this interview plan before scheduling?",
            "interview_plan": state["interview_plan"],
            "allowed_actions": ["approve", "reject"],
        }
    )
    action = str(decision.get("action", "reject")).lower() if isinstance(decision, dict) else str(decision).lower()
    if action == "approve":
        return {"status": "interviews_approved", "approvals": {"interviews": "approved"}, "audit_log": ["Human approved the interview plan."]}
    return {"status": "stopped", "approvals": {"interviews": "rejected"}, "audit_log": ["Human rejected the interview plan."]}


def route_after_interviews(state: RecruitmentState) -> Literal["offer", "stop"]:
    return "offer" if state.get("status") == "interviews_approved" else "stop"


def offer_agent(state: RecruitmentState) -> dict:
    """Agent 5: draft, but do not send, an offer for human review."""
    selected = state["shortlist"][0]
    offer = {
        "candidate_id": selected["candidate_id"],
        "candidate_name": selected["name"],
        "role": state["role"],
        "salary_range": "$110,000-$130,000",
        "start_date": "To be agreed",
        "status": "draft",
    }
    return {"offer": offer, "audit_log": ["Offer agent drafted an offer; nothing was sent."]}


def offer_approval(state: RecruitmentState) -> dict:
    """Human gate 3: final approval before an offer could be released."""
    decision = interrupt(
        {
            "phase": "offer_approval",
            "question": "Approve this offer for release to the candidate?",
            "offer": state["offer"],
            "allowed_actions": ["approve", "reject"],
        }
    )
    action = str(decision.get("action", "reject")).lower() if isinstance(decision, dict) else str(decision).lower()
    if action == "approve":
        return {"status": "offer_approved", "approvals": {"offer": "approved"}, "audit_log": ["Human approved the offer."]}
    return {"status": "stopped", "approvals": {"offer": "rejected"}, "audit_log": ["Human rejected the offer."]}


def route_after_offer(state: RecruitmentState) -> Literal["finalize", "stop"]:
    return "finalize" if state.get("status") == "offer_approved" else "stop"


def finalize_agent(state: RecruitmentState) -> dict:
    """Agent 6: summarize the completed workflow for the recruiter."""
    return {
        "status": "completed",
        "final_message": f"Recruitment workflow completed for {state['role']}. Offer approved for {state['offer']['candidate_name']}.",
        "audit_log": ["Workflow finalized after all required approvals."],
    }


def stopped(state: RecruitmentState) -> dict:
    """Terminal node used when a human rejects a phase."""
    return {"final_message": f"Workflow stopped after human rejection. Status: {state.get('status', 'stopped')}."}


def build_graph():
    """Build, connect, and compile the approval-aware StateGraph."""
    builder = StateGraph(RecruitmentState)
    builder.add_node("intake", intake_agent)
    builder.add_node("source", sourcing_agent)
    builder.add_node("screen", screening_agent)
    builder.add_node("shortlist_approval", shortlist_approval)
    builder.add_node("interviews", interview_agent)
    builder.add_node("interview_approval", interview_approval)
    builder.add_node("offer", offer_agent)
    builder.add_node("offer_approval", offer_approval)
    builder.add_node("finalize", finalize_agent)
    builder.add_node("stopped", stopped)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "source")
    builder.add_edge("source", "screen")
    builder.add_edge("screen", "shortlist_approval")
    builder.add_conditional_edges("shortlist_approval", route_after_shortlist, {"interviews": "interviews", "stop": "stopped"})
    builder.add_edge("interviews", "interview_approval")
    builder.add_conditional_edges("interview_approval", route_after_interviews, {"offer": "offer", "stop": "stopped"})
    builder.add_edge("offer", "offer_approval")
    builder.add_conditional_edges("offer_approval", route_after_offer, {"finalize": "finalize", "stop": "stopped"})
    builder.add_edge("finalize", END)
    builder.add_edge("stopped", END)

    return builder.compile(checkpointer=InMemorySaver())
