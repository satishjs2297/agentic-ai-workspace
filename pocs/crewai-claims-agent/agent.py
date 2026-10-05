"""CrewAI claims agent that reuses the shared Claim MCP server."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Type

# This simple local demo does not need CrewAI telemetry or network tracing.
# Set it before importing CrewAI so its telemetry setup sees the setting.
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field


DEFAULT_MCP_PROJECT = Path(__file__).resolve().parents[1] / "langgraph-mcp-claims"


def is_claims_question(instruction: str) -> bool:
    """Route claims work to MCP with a transparent educational rule."""
    text = instruction.lower()
    return any(term in text for term in ("claim", "member", "payment", "insurance", "clm", "mem"))


def server_parameters() -> StdioServerParameters:
    """Tell CrewAI's MCP adapter how to launch the existing MCP server."""
    mcp_project = Path(os.getenv("CLAIMS_MCP_PROJECT", str(DEFAULT_MCP_PROJECT)))
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(mcp_project),
    )


class ClaimInput(BaseModel):
    """Arguments accepted by the claim lookup MCP tools."""

    claim_id: str = Field(description="The claim identifier, for example CLM1001")


class MemberInput(BaseModel):
    """Arguments accepted by the member lookup MCP tool."""

    member_id: str = Field(description="The member identifier, for example MEM1001")


async def _call_mcp_tool(name: str, arguments: dict[str, str]) -> str:
    """Use the current official MCP Python client to call the shared server."""
    async with stdio_client(server_parameters()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            if result.is_error:
                return json.dumps({"error": f"MCP tool {name} returned an error."})
            text_parts = [block.text for block in result.content if hasattr(block, "text")]
            return "\n".join(text_parts) or json.dumps(result.structured_content or {})


class GetClaimTool(BaseTool):
    """CrewAI tool wrapper for the Claim MCP get_claim tool."""

    name: str = "get_claim"
    description: str = "Get the status and details of a claim from the Claim MCP server."
    args_schema: Type[BaseModel] = ClaimInput

    def _run(self, claim_id: str) -> str:
        return asyncio.run(_call_mcp_tool("get_claim", {"claim_id": claim_id}))


class GetMemberTool(BaseTool):
    """CrewAI tool wrapper for the Claim MCP get_member tool."""

    name: str = "get_member"
    description: str = "Get member information from the Claim MCP server."
    args_schema: Type[BaseModel] = MemberInput

    def _run(self, member_id: str) -> str:
        return asyncio.run(_call_mcp_tool("get_member", {"member_id": member_id}))


class GetClaimPaymentTool(BaseTool):
    """CrewAI tool wrapper for the Claim MCP get_claim_payment tool."""

    name: str = "get_claim_payment"
    description: str = "Get payment information for a claim from the Claim MCP server."
    args_schema: Type[BaseModel] = ClaimInput

    def _run(self, claim_id: str) -> str:
        return asyncio.run(_call_mcp_tool("get_claim_payment", {"claim_id": claim_id}))


def claim_mcp_tools() -> list[BaseTool]:
    """Expose the three MCP calls as normal CrewAI tools."""
    return [GetClaimTool(), GetMemberTool(), GetClaimPaymentTool()]


def run_crew(instruction: str, tools=None) -> str:
    """Create one simple CrewAI agent and run one task."""
    agent = Agent(
        role="Claims assistant" if tools else "General assistant",
        goal="Answer the user's instruction accurately and clearly.",
        backstory=(
            "You answer claims questions using the provided Claim MCP tools and "
            "must not invent claim data."
            if tools
            else "You are a helpful general-purpose assistant."
        ),
        tools=tools or [],
        llm="gpt-4o-mini",
        allow_delegation=False,
        verbose=False,
    )
    task = Task(
        description=instruction,
        expected_output="A concise, accurate natural-language answer to the user.",
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff()
    return getattr(result, "raw", str(result))


def process_instruction(instruction: str) -> str:
    """Use CrewAI directly for general prompts or with MCP tools for claims."""
    if not is_claims_question(instruction):
        return run_crew(instruction)

    # These wrappers remain CrewAI tools, but each call crosses the official
    # current MCP client boundary to the existing Claim MCP server.
    return run_crew(instruction, tools=claim_mcp_tools())
