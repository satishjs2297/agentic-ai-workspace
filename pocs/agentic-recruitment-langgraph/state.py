"""Shared state for the multi-agent recruitment workflow."""

import operator
from typing import Annotated, Any, TypedDict


class RecruitmentState(TypedDict, total=False):
    """The shared case file passed between recruitment agents.

    Each LangGraph node reads the fields it needs and returns only updates.
    ``audit_log`` uses an append reducer so every phase contributes a durable
    explanation of what happened.
    """

    request: str
    role: str
    job_summary: str
    candidates: list[dict[str, Any]]
    shortlist: list[dict[str, Any]]
    interview_plan: dict[str, Any]
    offer: dict[str, Any]
    approvals: dict[str, str]
    audit_log: Annotated[list[str], operator.add]
    status: str
    final_message: str
