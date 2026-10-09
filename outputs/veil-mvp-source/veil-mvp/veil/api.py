"""FastAPI entry point for the Veil MVP."""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from veil.gateway import VeilGateway

app = FastAPI(
    title="Veil Privacy Gateway",
    description="Local demo of reversible PII protection for agent tool calls.",
    version="0.1.0",
)
gateway = VeilGateway()


class ToolCallRequest(BaseModel):
    tool_name: str = Field(default="simulated_tool", min_length=1, max_length=80)
    payload: Any


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small health response for setup checks."""
    return {"status": "ok", "service": "veil"}


@app.post("/tool-call")
def tool_call(request: ToolCallRequest) -> dict[str, object]:
    """Demonstrate the sanitized request boundary with the local mock tool."""
    context = gateway.start_task()
    try:
        return gateway.call_tool(context, request.tool_name, request.payload).to_dict()
    finally:
        gateway.close_task(context)

