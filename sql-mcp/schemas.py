from pydantic import BaseModel
from typing import List, Dict, Any, Optional


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