"""A tiny MCP server backed by plain Python dictionaries."""

from mcp.server import MCPServer


mcp = MCPServer("claims-demo-server")

MEMBERS = {
    "MEM1001": {"member_id": "MEM1001", "name": "Avery Johnson", "plan": "Gold PPO"},
    "MEM1002": {"member_id": "MEM1002", "name": "Morgan Lee", "plan": "Silver HMO"},
}

CLAIMS = {
    "CLM1001": {"claim_id": "CLM1001", "member_id": "MEM1001", "service": "Annual wellness visit", "status": "Approved", "billed_amount": 250.00},
    "CLM1002": {"claim_id": "CLM1002", "member_id": "MEM1002", "service": "Physical therapy", "status": "In review", "billed_amount": 480.00},
}

PAYMENTS = {
    "CLM1001": {"claim_id": "CLM1001", "payment_id": "PAY9001", "amount": 225.00, "paid_on": "2026-09-15", "method": "ACH"},
    "CLM1002": {"claim_id": "CLM1002", "payment_id": None, "amount": 0.00, "paid_on": None, "method": None},
}


@mcp.tool()
async def get_claim(claim_id: str) -> dict:
    """Return one claim from the in-memory mock dataset."""
    return CLAIMS.get(claim_id, {"error": f"Claim {claim_id} was not found."})


@mcp.tool()
async def get_member(member_id: str) -> dict:
    """Return one member from the in-memory mock dataset."""
    return MEMBERS.get(member_id, {"error": f"Member {member_id} was not found."})


@mcp.tool()
async def get_claim_payment(claim_id: str) -> dict:
    """Return the payment record for a claim from the mock dataset."""
    return PAYMENTS.get(claim_id, {"error": f"No payment record for {claim_id}."})


if __name__ == "__main__":
    # stdio lets the application launch this file as a child process and
    # communicate with it through the official MCP protocol.
    mcp.run(transport="stdio")
