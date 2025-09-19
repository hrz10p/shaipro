from typing import Optional, List, Literal, TypedDict, Any, Dict

class GraphState(TypedDict, total=False):
    user_input: str
    context: Dict[str, Any]
    route: Optional[Literal["sql_query", "other"]]
    sql: Optional[str]
    exec_result: Optional[Dict[str, Any]]
    intermediate_steps: List[Dict[str, Any]]
    final_text: Optional[str]
