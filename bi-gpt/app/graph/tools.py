from typing import Any, Type
from pydantic import BaseModel, Field, PrivateAttr
# РЕКОМЕНДУЕМЫЙ импорт для LC 0.3+
from langchain_core.tools import BaseTool

from app.agent.tools import (
    SQLExecTool, SQLExplainTool, SQLMetaInfoTool, SQLPoliciesTool
)

# ======= Schemas =======

class ExecInput(BaseModel):
    sql: str = Field(..., description="SQL query to execute")

class ExplainInput(BaseModel):
    sql: str = Field(..., description="SQL query to explain")

# ======= Tools =======

class SQLExecLangTool(BaseTool):
    name: str = "sql_exec"
    description: str = "Execute a safe SELECT SQL against the BI database"
    args_schema: Type[BaseModel] = ExecInput

    _inner: SQLExecTool = PrivateAttr()

    def __init__(self, inner: SQLExecTool, **data: Any):
        super().__init__(**data)
        self._inner = inner

    async def _arun(self, sql: str) -> Any:
        return await self._inner.run({"sql": sql})

    def _run(self, sql: str) -> Any:  # sync путь не используем
        raise NotImplementedError


class SQLExplainLangTool(BaseTool):
    name: str = "sql_explain"
    description: str = "Explain a SQL query to estimate cost/rows/violations"
    args_schema: Type[BaseModel] = ExplainInput

    _inner: SQLExplainTool = PrivateAttr()

    def __init__(self, inner: SQLExplainTool, **data: Any):
        super().__init__(**data)
        self._inner = inner

    async def _arun(self, sql: str) -> Any:
        return await self._inner.run({"sql": sql})

    def _run(self, sql: str) -> Any:
        raise NotImplementedError


class SQLMetaInfoLangTool(BaseTool):
    name: str = "sql_metainfo"
    description: str = "Get DB schema (tables, columns, enums)"
    # нет входных аргументов → без args_schema (BaseTool сам примет пустые kwargs)

    _inner: SQLMetaInfoTool = PrivateAttr()

    def __init__(self, inner: SQLMetaInfoTool, **data: Any):
        super().__init__(**data)
        self._inner = inner

    async def _arun(self) -> Any:
        return await self._inner.run({})

    def _run(self) -> Any:
        raise NotImplementedError


class SQLPoliciesLangTool(BaseTool):
    name: str = "sql_policies"
    description: str = "Get policies (allow_tables, deny_columns, glossary, limits)"
    # входных аргументов нет

    _inner: SQLPoliciesTool = PrivateAttr()

    def __init__(self, inner: SQLPoliciesTool, **data: Any):
        super().__init__(**data)
        self._inner = inner

    async def _arun(self) -> Any:
        return await self._inner.run({})

    def _run(self) -> Any:
        raise NotImplementedError


class AbracadabraLangTool(BaseTool):
    name: str = "abracadabra"
    description: str = "Test tool to count down and then ask about dumplings"
    _inner: Any

    def __init__(self, inner):
        super().__init__()
        self._inner = inner

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async interface")

    async def _arun(self, *args, **kwargs) -> dict:
        # просто проксируем к inner.run()
        return await self._inner.run()