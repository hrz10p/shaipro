from __future__ import annotations

from typing import Any, Dict, Optional

from ..clients.http_client import SqlAdapterClient, QueryResult, ExplainResult, MetaInfo, PolicyInfo


class ToolExecutionError(Exception):
    pass


class SQLExecTool:
    name = "sql_exec"
    description = "Execute a SQL query against the database. Only SELECT statements are allowed."

    def __init__(self, sql_client: SqlAdapterClient) -> None:
        self.sql_client = sql_client

    async def run(self, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        if params is None:
            params = {}
        sql = params.get("sql", "")
        if not sql:
            raise ToolExecutionError("SQL query is required")
        
        try:
            result = await self.sql_client.exec(sql)
            return result
        except Exception as exc:
            raise ToolExecutionError(str(exc))


class SQLExplainTool:
    name = "sql_explain"
    description = "Get execution plan and analysis for a SQL query."

    def __init__(self, sql_client: SqlAdapterClient) -> None:
        self.sql_client = sql_client

    async def run(self, params: Optional[Dict[str, Any]] = None) -> ExplainResult:
        if params is None:
            params = {}
        sql = params.get("sql", "")
        if not sql:
            raise ToolExecutionError("SQL query is required")
        
        try:
            result = await self.sql_client.explain(sql)
            return result
        except Exception as exc:
            raise ToolExecutionError(str(exc))


class SQLMetaInfoTool:
    name = "sql_metainfo"
    description = "Get database metadata including tables, columns, and database information."

    def __init__(self, sql_client: SqlAdapterClient) -> None:
        self.sql_client = sql_client

    async def run(self, params: Optional[Dict[str, Any]] = None) -> MetaInfo:
        try:
            result = await self.sql_client.get_metainfo()
            return result
        except Exception as exc:
            raise ToolExecutionError(str(exc))


class SQLPoliciesTool:
    name = "sql_policies"
    description = "Get database access policies including allowed tables, columns, functions, and business metrics."

    def __init__(self, sql_client: SqlAdapterClient) -> None:
        self.sql_client = sql_client

    async def run(self, params: Optional[Dict[str, Any]] = None) -> PolicyInfo:
        try:
            result = await self.sql_client.get_policies()
            return result
        except Exception as exc:
            raise ToolExecutionError(str(exc))
