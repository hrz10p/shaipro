from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the agent")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context for the agent")


class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    tool_result: Optional[Any] = None
    success: bool
