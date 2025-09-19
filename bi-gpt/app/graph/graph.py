from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .state import GraphState
from .tools import (
    SQLExecLangTool, SQLExplainLangTool, SQLMetaInfoLangTool, SQLPoliciesLangTool, AbracadabraLangTool,
)
from app.agent.tools import (
    SQLExecTool, SQLExplainTool, SQLMetaInfoTool, SQLPoliciesTool, AbracadabraTool,
)
from app.config import AppConfig


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
    "- Never use SELECT * or COUNT(*). Use explicit allowed columns and COUNT(column).\n"
    "- Respect deny_columns (PII), allow_tables, allow_functions, join-graph.\n"
    "- Add LIMIT for wide scans.\n"
    "- Return ONLY SQL. No markdown fences, no explanations."
)

ANALYSER_SYSTEM = (
    "You summarise SQL results for end users in their language. "
    "Explain briefly what the numbers mean. Do not expose internal policies or the SQL text."
)


# ---------- LLM FACTORY ----------

def _make_llm(config: AppConfig) -> ChatOpenAI:
    # Никаких лишних kwargs; tool_choice управим на этапе bind_tools
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


def _to_text(x: Any) -> str:
    return (getattr(x, "content", None) or str(x or "")).strip()


# ---------- GRAPH ----------

def build_bigpt_graph(sql_client, config: AppConfig):
    llm = _make_llm(config)

    # Инициализируем реальные тулы, которые ходят к sql-proxy
    t_exec = SQLExecLangTool(SQLExecTool(sql_client))
    t_explain = SQLExplainLangTool(SQLExplainTool(sql_client))
    t_meta = SQLMetaInfoLangTool(SQLMetaInfoTool(sql_client))
    t_policies = SQLPoliciesLangTool(SQLPoliciesTool(sql_client))

    t_abracadabra = AbracadabraLangTool(AbracadabraTool())

    # Привязываем тулы к LLM, НО отключаем авто-вызов — у твоего сервера это ломается.
    # Так мы сохраняем совместимость интерфейсов, но вызываем тулы вручную в коде.
    llm_with_tools = llm.bind_tools([t_exec, t_explain, t_meta, t_policies], tool_choice="none")

    graph = StateGraph(GraphState)

    # --- classify ---
    async def n_classify(state: GraphState) -> GraphState:
        text = (state.get("user_input") or "").strip().lower()

        if "абрака-бабрака" in text:
            state["route"] = "abracadabra"
        else:
            # прежняя логика (если была LLM-классификация — можно оставить)
            # простой эвристикой чаще надёжнее:
            sql_markers = [
                "select", " from ", " join ", " where ", " group by", " order by", " limit ",
                "сколько", "посчитай", "подсчитай", "сумма", "среднее", "минимум", "максимум",
                "за последние", "по дням", "по неделям", "по месяцам", "транзакц", "выручк", "продаж",
            ]
            state["route"] = "sql_query" if any(m in text for m in sql_markers) else "other"

        state.setdefault("intermediate_steps", []).append(
            {"node": "classify", "output": state["route"]}
        )
        return state

    async def n_abracadabra(state: GraphState) -> GraphState:
        res = await t_abracadabra._arun()
        text = (res or {}).get("text") or "10\n9\n8\n7\n6\n5\n4\n3\n2\n1\nСколько кило пельмешек купить"
        state["final_text"] = text
        state.setdefault("intermediate_steps", []).append(
            {"node": "abracadabra", "output": text}
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

    # --- sql_generate (мета+политики через тулы, но вызываем вручную) ---
    async def n_sql_generate(state: GraphState) -> GraphState:
        metainfo = await t_meta._arun()         # dict/pydantic → приводим к строке в промпт
        policies = await t_policies._arun()

        msg = await sql_prompt.ainvoke({
            "user_input": state["user_input"],
            "metainfo": metainfo,
            "policies": policies,
        })
        # Используем llm_with_tools (хотя tool_choice=none) — это безвредно и унифицированно
        res = await llm_with_tools.ainvoke(msg)
        sql = _to_text(res)
        sql = sql.strip().strip("`").replace("```sql", "").replace("```", "").strip()

        state["sql"] = sql
        state.setdefault("intermediate_steps", []).append(
            {"node": "sql_generate", "sql": sql}
        )
        return state

    # --- exec (explain -> optional repair -> exec), тулы вызываем вручную ---
    async def n_exec(state: GraphState) -> GraphState:
        # 1) EXPLAIN
        explain = await t_explain._arun(sql=state["sql"])
        violations = getattr(explain, "violations", []) or []
        too_costly = getattr(explain, "tooCostly", False) or False

        # 2) Repair при необходимости
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
                {"node": "repair_sql", "sql": sql_fixed, "violations": violations, "too_costly": too_costly}
            )

        # 3) EXEC
        exec_result = await t_exec._arun(sql=state["sql"])
        row_count = getattr(exec_result, "rowCount", None) if exec_result else None

        state["exec_result"] = exec_result
        state.setdefault("intermediate_steps", []).append(
            {"node": "exec", "rows": row_count}
        )
        return state

    # --- analyse (LLM без tools) ---
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

    # ---------- assemble graph ----------
    graph.add_node("classify", n_classify)
    graph.add_node("chitchat", n_chitchat)
    graph.add_node("sql_generate", n_sql_generate)
    graph.add_node("exec", n_exec)
    graph.add_node("analyse", n_analyse)

    graph.add_node("abracadabra", n_abracadabra)


    graph.set_entry_point("classify")

    def route_edge(state: GraphState):
        return state.get("route", "other")

    graph.add_conditional_edges("classify", route_edge, {
        "abracadabra": "abracadabra",   # <— новая ветка
        "other": "chitchat",
        "sql_query": "sql_generate",
    })
    graph.add_edge("chitchat", END)
    graph.add_edge("sql_generate", "exec")
    graph.add_edge("exec", "analyse")
    graph.add_edge("analyse", END)

    return graph.compile()
