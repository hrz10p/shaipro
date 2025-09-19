from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    output: str
    route: str
    sql: str
    intermediate_steps: List[Dict[str, Any]]
    exec_result: Dict[str, Any]
    visualization: Optional[Dict[str, Any]] = None
