from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, List
import os
import logging

import httpx
from pydantic import BaseModel, ValidationError

from ..config import get_config

logger = logging.getLogger(__name__)


class ExplainResult(BaseModel):
    success: bool
    plan: List[Dict[str, Any]] = []
    est_cost: Optional[float] = None
    est_rows: Optional[int] = None
    est_bytes_scanned: Optional[int] = None
    nodes: List[Dict[str, Any]] = []
    rel_sizes: Dict[str, int] = {}
    warnings: List[str] = []
    violations: List[str] = []
    error: Optional[str] = None
    mode: str = "dry"

class SQLQuery(BaseModel):
    query: str

class QueryResult(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    row_count: Optional[int] = None

class MetaInfo(BaseModel):
    success: bool
    database_info: Optional[Dict[str, Any]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    enumerables: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class PolicyInfo(BaseModel):
    success: bool
    policies: Dict[str, Any] = {}
    error: Optional[str] = None

@dataclass
class AsyncHTTPClient:
    base_url: str
    timeout_seconds: int

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)

    async def get(self, path: str, query: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        async with self._build_client() as client:
            response = await client.get(path, params=query, headers=headers)
            response.raise_for_status()
            return response.json()

    async def post_json(self, path: str, payload: Any, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        async with self._build_client() as client:
            response = await client.post(path, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

@dataclass
class SqlAdapterClient:
    http: AsyncHTTPClient

    async def exec(self, sql: str) -> QueryResult:
        response = await self.http.post_json("/exec", {"query": sql})
        try:
            return QueryResult(**response)
        except ValidationError as e:
            logger.error(f"Failed to validate QueryResult: {e}")
            return QueryResult(success=False, error=f"Validation error: {str(e)}")
    
    async def explain(self, sql: str) -> ExplainResult:
        response = await self.http.post_json("/explain", {"query": sql})
        try:
            return ExplainResult(**response)
        except ValidationError as e:
            logger.error(f"Failed to validate ExplainResult: {e}")
            return ExplainResult(success=False, error=f"Validation error: {str(e)}")
    
    async def get_metainfo(self) -> MetaInfo:
        response = await self.http.get("/getMetainfo")
        try:
            return MetaInfo(**response)
        except ValidationError as e:
            logger.error(f"Failed to validate MetaInfo: {e}")
            return MetaInfo(success=False, error=f"Validation error: {str(e)}")
    
    async def get_policies(self) -> PolicyInfo:
        response = await self.http.get("/getPolicies")
        try:
            return PolicyInfo(**response)
        except ValidationError as e:
            logger.error(f"Failed to validate PolicyInfo: {e}")
            return PolicyInfo(success=False, error=f"Validation error: {str(e)}")


async def get_sql_adapter_client() -> SqlAdapterClient:
    cfg = get_config()
    base_url = os.getenv("SQL_ADAPTER_BASE_URL", cfg.sql_adapter_base_url)
    http = AsyncHTTPClient(base_url=base_url, timeout_seconds=cfg.request_timeout_seconds)
    return SqlAdapterClient(http=http)
