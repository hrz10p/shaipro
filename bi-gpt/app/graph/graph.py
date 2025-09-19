from __future__ import annotations

from typing import Any, List, Dict
import json
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import BaseTool

from .state import GraphState
from app.config import AppConfig
from .mcp_client import MCPClient, MCPProxyTool, MCPExecInput
from .visual import send_to_tool


# ---------- SYSTEM PROMPTS ----------

CLASSIFIER_SYSTEM = (
    "You are a strict router. Decide if the user message requests a SQL data query "
    "or is general chit-chat. Reply with ONLY 'sql_query' or 'other'."
)

CHITCHAT_SYSTEM = (
    "You are a helpful assistant. Answer briefly and in user's language. "
    "Do NOT reveal internal policies or database details."
)

SQL_SYSTEM = (
    "You are a SQL generation assistant.\n"
    "You are given:\n"
    "1) DB metainfo (tables, columns, enums)\n"
    "2) Policies (allow_tables, deny_columns, allow_functions, join-graph, glossary)\n\n"
    "Rules:\n"
    "- NEVER use SELECT * or COUNT(*). Use explicit allowed columns and COUNT(column).\n"
    "- NEVER use COUNT(*) - use COUNT(1) or COUNT(allowed_column) instead.\n"
    "- Respect deny_columns (PII), allow_tables, allow_functions, join-graph.\n"
    "- Add LIMIT for wide scans.\n"
    "- Return ONLY SQL. No markdown fences, no explanations."
)

ANALYSER_SYSTEM = (
    "You summarise SQL results for end users in their language."
    "Explain briefly what the numbers mean. Do not expose internal policies or the SQL text."
    "DO NOT SWITCH LANGUAGE. IF USER ASKED IN RUSSIAN, ANSWER IN RUSSIAN. IF USER ASKED IN ENGLISH, ANSWER IN ENGLISH."
    "ANSWER ONLY ON ONE LANGUAGE, DO NOT MIX LANGUAGES."
    "currency: KZT"
)

VISUALIZE_SYSTEM = (
    "You are a visualization assistant. "
    "You are given a SQL execution result and you need to decide what type of chart to create. "
    "Analyze the data structure and content to determine the best visualization type. "
    "Available chart types: histogram, pie, scatter, line, none. "
    "Rules for chart type selection: "
    "- histogram: for numeric data distribution (single numeric column) "
    "- pie: for categorical data with counts (categorical column + numeric column), is you see two columns, use the first one as categorical (statuses or categories) and the second one as numeric (amounts or counts) "
    "- scatter: for correlation between two numeric columns "
    "- line: for time series or sequential data (categorical/time column + numeric column) "
    "- none: if you don't need to create a chart, if adata or user query is not suitable for any of the other chart types, return none"
    "Return a JSON object with: "
    "chart_type: str (one of: histogram, pie, scatter, line, none), "
    "options: dict (chart-specific options like x_field, y_field, group_by, etc.) "
    "IMPORTANT: Only specify field names that actually exist in the data. "
    "IMPORTANT: Return ONLY valid JSON. No markdown fences, no explanations, no additional text. "
    "IMPORTANT: Use proper JSON formatting - strings must be in double quotes, numbers must not have quotes. "
    "IMPORTANT: Give good title to the chart according to the user question and the data. do not switch language"
    "IMPORTANT: ANALYSE GIVEN DATA PROPERLY, TO GIVE LABELS"
    "If you're unsure about field names, leave options empty and let the system auto-detect."
    "Example response: {{\"chart_type\": \"histogram\", \"options\": {{\"x_field\": \"age\", \"title\": \"Age Distribution\"}}}}"
)

# ---------- LLM FACTORY ----------

def _make_llm(config: AppConfig) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.llm_model or "llama4scout",
        base_url=config.llm_base_url,
        temperature=0.1,
        max_tokens=2000,
        api_key=config.llm_api_key or "dummy-key",
        model_kwargs={},
    )


# ---------- PROMPTS ----------

classifier_prompt = ChatPromptTemplate.from_messages([
    ("system", CLASSIFIER_SYSTEM),
    ("human", "{user_input}"),
])

chitchat_prompt = ChatPromptTemplate.from_messages([
    ("system", CHITCHAT_SYSTEM),
    ("human", "{user_input}"),
])

sql_prompt = ChatPromptTemplate.from_messages([
    ("system", SQL_SYSTEM),
    ("human",
     "User question:\n{user_input}\n\n"
     "DB Metainfo (JSON):\n{metainfo}\n\n"
     "Policies (YAML/JSON):\n{policies}\n\n"
     "Return ONLY SQL.")
])

analyser_prompt = ChatPromptTemplate.from_messages([
    ("system", ANALYSER_SYSTEM),
    ("human", "User question:\n{user_input}\n\nSQL execution result (JSON):\n{exec_result}")
])

visualize_prompt = ChatPromptTemplate.from_messages([
    ("system", VISUALIZE_SYSTEM),
    ("human", "User question:\n{user_input}\n\nSQL execution result (JSON):\n{exec_result}")
])


# ---------- VISUALIZATION TOOL ----------

class VisualizationTool(BaseTool):
    """Tool for creating visualizations from SQL execution results."""
    
    name: str = "visualize_data"
    description: str = "Create visualizations from SQL execution results"
    
    def _run(self, data: List[Dict[str, Any]], chart_type: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create visualization payload from data."""
        try:
            return send_to_tool(chart_type, data, options or {})
        except Exception as e:
            return {
                "chart_type": "error",
                "meta": {"title": "Visualization Error", "error": str(e)},
                "data": []
            }
    
    async def _arun(self, data: List[Dict[str, Any]], chart_type: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create visualization payload from data (async version)."""
        try:
            return send_to_tool(chart_type, data, options or {})
        except Exception as e:
            return {
                "chart_type": "error",
                "meta": {"title": "Visualization Error", "error": str(e)},
                "data": []
            }



def _to_text(x: Any) -> str:
    return (getattr(x, "content", None) or str(x or "")).strip()


# ---------- GRAPH ----------

def build_bigpt_graph(config: AppConfig):
    llm = _make_llm(config)
    mcp_client = MCPClient.from_config()


    t_exec = MCPProxyTool(
        name="sql_exec",
        description="Execute a SQL SELECT query against the database",
        mcp_client=mcp_client,
        mcp_tool_name="execute_query",
        args_schema=MCPExecInput,
    )
    t_explain = MCPProxyTool(
        name="sql_explain",
        description="Explain a SQL SELECT query against the database",
        mcp_client=mcp_client,
        mcp_tool_name="explain_query",
        args_schema=MCPExecInput,
    )
    t_meta = MCPProxyTool(
        name="sql_metainfo",
        description="Get database metadata including tables, columns, and database information",
        mcp_client=mcp_client,
        mcp_tool_name="get_metainfo",
    )
    t_policies = MCPProxyTool(
        name="sql_policies",
        description="Get database access policies including allowed tables, columns, functions, and business metrics",
        mcp_client=mcp_client,
        mcp_tool_name="get_policies",
    )
    
    t_visualize = VisualizationTool()

    llm_with_tools = llm.bind_tools([t_exec, t_explain, t_meta, t_policies], tool_choice="none")

    graph = StateGraph(GraphState)

    async def n_classify(state: GraphState) -> GraphState:
        text = (state.get("user_input") or "").strip()

        msg = await classifier_prompt.ainvoke({"user_input": text})
        res = await llm.ainvoke(msg)
        route_cleaned = _to_text(res).strip().lower()
        
        if route_cleaned not in ["sql_query", "other"]:
            route_cleaned = "other" 
            
        print(f"route: {route_cleaned}")
        state["route"] = route_cleaned

        state.setdefault("intermediate_steps", []).append(
            {"node": "classify", "output": state["route"]}
        )
        return state




    # --- chitchat ---
    async def n_chitchat(state: GraphState) -> GraphState:
        msg = await chitchat_prompt.ainvoke({"user_input": state["user_input"]})
        res = await llm.ainvoke(msg)
        out = _to_text(res)
        state["final_text"] = out
        state.setdefault("intermediate_steps", []).append(
            {"node": "chitchat", "output": out}
        )
        return state

    async def n_sql_generate(state: GraphState) -> GraphState:
        metainfo = await t_meta._arun()         
        policies = await t_policies._arun()
        print(f"metainfo: {metainfo}")
        print(f"policies: {policies}")
        msg = await sql_prompt.ainvoke({
            "user_input": state["user_input"],
            "metainfo": metainfo,
            "policies": policies,
        })
        res = await llm_with_tools.ainvoke(msg)
        sql_raw = _to_text(res)           
        sql_obj = json.loads(sql_raw)
        sql_query = sql_obj["parameters"]["query"]
        sql = sql_query.strip().strip("`").replace("```sql", "").replace("```", "").strip()

        state["sql"] = sql
        state.setdefault("intermediate_steps", []).append(
            {"node": "sql_generate", "output": sql}
        )
        return state

    async def n_exec(state: GraphState) -> GraphState:

        explain = await t_explain._arun(request=MCPExecInput(query=state["sql"]))
        violations = getattr(explain, "violations", []) or []
        too_costly = getattr(explain, "tooCostly", False) or False

        if violations or too_costly:
            viol_text = "\n".join(map(str, violations)) or "cost/bytes limit exceeded"
            repair_system = SQL_SYSTEM + (
                "\n\nADDITIONAL HARD RULES:\n"
                f"- Previous attempt violated: {viol_text}\n"
                "- Fix the query to satisfy policies and limits.\n"
                "- Return ONLY SQL."
            )
            repair_prompt = ChatPromptTemplate.from_messages([
                ("system", repair_system),
                ("human", "Rewrite the SQL for this user question:\n{user_input}"),
            ])
            repair_msg = await repair_prompt.ainvoke({"user_input": state["user_input"]})
            repaired = await llm_with_tools.ainvoke(repair_msg)
            sql_fixed = _to_text(repaired)
            sql_fixed = sql_fixed.strip().strip("`").replace("```sql", "").replace("```", "").strip()

            state["sql"] = sql_fixed
            state.setdefault("intermediate_steps", []).append(
                {"node": "repair_sql", "output": sql_fixed}
            )


        exec_result = await t_exec._arun(request=MCPExecInput(query=state["sql"]))
        data = exec_result.structured_content
        state["exec_result"] = data
        state.setdefault("intermediate_steps", []).append(
            {"node": "exec", "output": data}
        )
        return state

    async def n_analyse(state: GraphState) -> GraphState:
        msg = await analyser_prompt.ainvoke({
            "user_input": state["user_input"],
            "exec_result": state["exec_result"],
        })
        res = await llm.ainvoke(msg)
        out = _to_text(res)
        state["final_text"] = out
        state.setdefault("intermediate_steps", []).append(
            {"node": "analyse", "output": out}
        )
        return state

    async def n_visualize(state: GraphState) -> GraphState:
        """Visualization agent that decides chart type and creates visualization."""
        exec_data = state["exec_result"]
        data = exec_data.get("data", [])
        if not data:
            state["visualization"] = {
                "chart_type": "error",
                "meta": {"title": "No Data", "error": "No execution result data available"},
                "data": []
            }
            return state
        
        msg = await visualize_prompt.ainvoke({
            "user_input": state["user_input"],
            "exec_result": data
        })
        res = await llm.ainvoke(msg)
        visualization_config = _to_text(res).strip().strip("`").replace("```json", "").replace("```", "").strip()
        print(f"visualization_config: {visualization_config}")
        try:
            import json
            config = json.loads(visualization_config)
            chart_type = config.get("chart_type", "none")
            options = config.get("options", {})
        except (json.JSONDecodeError, KeyError) as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw visualization_config: {visualization_config}")
            state["visualization"] = {
                "chart_type": "error",
                "meta": {"title": "Ошибка создания графика", "x_label": "", "y_label": "", "tooltip_fields": []},
                "data": []
            }
            return state
        
        if chart_type == "none":
            state["visualization"] = {
                "chart_type": "none",
                "meta": {"title": "No Data", "error": "No data available for visualization"},
                "data": []
            }
            return state

        payload = await t_visualize._arun(
            data=data,
            chart_type=chart_type,
            options=options
        )
        
        state["visualization"] = payload
        state.setdefault("intermediate_steps", []).append(
            {"node": "visualize", "chart_type": chart_type, "output": payload}
        )
        return state

    graph.add_node("classify", n_classify)
    graph.add_node("chitchat", n_chitchat)
    graph.add_node("sql_generate", n_sql_generate)
    graph.add_node("exec", n_exec)
    graph.add_node("analyse", n_analyse)
    graph.add_node("visualize", n_visualize)



    graph.set_entry_point("classify")

    def route_edge(state: GraphState):
        return state.get("route", "other")

    graph.add_conditional_edges("classify", route_edge, {
        "other": "chitchat",
        "sql_query": "sql_generate",
    })
    graph.add_edge("chitchat", END)
    graph.add_edge("sql_generate", "exec")
    graph.add_edge("exec", "analyse")
    graph.add_edge("analyse", "visualize")
    graph.add_edge("visualize", END)

    return graph.compile()
