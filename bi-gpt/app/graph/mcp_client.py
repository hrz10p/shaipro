from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from fastmcp import Client

from ..config import get_config

class MCPClient:
    def __init__(self, url: str):
        self.client = Client(url)   

    @classmethod
    def from_config(cls):
        cfg = get_config()
        return cls(url=cfg.mcp_url or "http://localhost:8001/mcp")

    async def list_tools(self):
        async with self.client:
            result = await self.client.list_tools()
            return result

    async def call(self, tool_name: str, kwargs: dict):
        async with self.client:
            result = await self.client.call_tool(tool_name, kwargs)
            return result

class MCPExecInput(BaseModel):
    query: str = Field(..., description="SQL query to execute")

class MCPProxyTool(BaseTool):
    name: str
    description: str
    mcp_client: Any
    mcp_tool_name: str
    args_schema: Optional[Type[BaseModel]] = None

    def _run(self, *args, **kwargs):
        return self.mcp_client.call(self.mcp_tool_name, kwargs).result()

    async def _arun(self, *args, **kwargs):
        return await self.mcp_client.call(self.mcp_tool_name, kwargs)
