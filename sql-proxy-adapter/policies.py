import yaml
import os
from typing import Any, Dict, List, Optional

POLICY_FILE = os.getenv("POLICY_FILE", "policies.yaml")


class PolicyManager:
    def __init__(self, path: str = POLICY_FILE):
        self.path = path
        self._data: Dict[str, Any] = {}
        self.reload()

    def reload(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Policy file not found: {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    @property
    def allow_tables(self) -> List[str]:
        return self._data.get("allow_tables", [])

    @property
    def deny_columns(self) -> List[str]:
        return self._data.get("deny_columns", [])

    @property
    def allow_functions(self) -> List[str]:
        return self._data.get("allow_functions", [])

    @property
    def join_graph(self) -> List[Dict[str, str]]:
        return self._data.get("join_graph", [])

    @property
    def limits(self) -> Dict[str, Any]:
        return self._data.get("limits", {})

    @property
    def glossary(self) -> Dict[str, Dict[str, Any]]:
        return self._data.get("glossary", {})

    def map_term(self, term: str) -> Optional[Dict[str, Any]]:
        return self.glossary.get(term.lower())
    
    def get_metric_formula(self, term: str) -> Optional[str]:
        metric = self.map_term(term)
        return metric.get("formula") if metric else None
    
    def get_metric_tables(self, term: str) -> List[str]:
        metric = self.map_term(term)
        return metric.get("tables", []) if metric else []
    
    def get_metric_grain(self, term: str) -> List[str]:
        metric = self.map_term(term)
        return metric.get("grain", []) if metric else []
    
    def get_metric_filter(self, term: str) -> Optional[str]:
        metric = self.map_term(term)
        return metric.get("filter") if metric else None

    def validate_table(self, table: str) -> bool:
        return table in self.allow_tables

    def validate_column(self, column: str) -> bool:
        return column not in self.deny_columns

    @property
    def enumerables(self) -> List[str]:
        return self._data.get("enumerables", [])


policy_manager = PolicyManager()
