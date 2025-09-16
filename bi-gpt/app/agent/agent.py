from __future__ import annotations

import os
from typing import Any, Dict, Optional, List
from dataclasses import dataclass

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from pydantic import Field

from .tools import SQLExecTool, SQLExplainTool, SQLMetaInfoTool, SQLPoliciesTool
from ..clients.http_client import SqlAdapterClient


class SimpleSQLAgent:
    
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.schema_info = None
        self.policies_info = None
    
    async def ainvoke(self, inputs):
        user_query = inputs.get("input", "")


        classifier_prompt = f"""
                            Classify the user query. Categories:
                            - sql_query → for data/metrics/DB requests
                            - other → for chit-chat, greetings, or anything else

                            Examples:
                            User: "Сколько транзакций было за вчера?" → sql_query
                            User: "дай средний баланс по премиум клиентам" → sql_query
                            User: "Кто ты?" → other
                            User: "Привет" → other
                            User: "как дела?" → other

                            Now classify:
                            User query: {user_query}
                            Answer only one word: sql_query or other
                            """

        classifier_response = await self.llm.ainvoke(classifier_prompt)

        print(f"Classifier response: {classifier_response.content.strip()}")

        if classifier_response.content.strip() == "sql_query":
            pass
        elif classifier_response.content.strip() == "other":
            chatter_prompt = f""" You are a helper bot for BI-GPT, your role is to chat with the user if he is writing anything, but not requesting for data. Just talk with the user, be polite and talk with the user on language of user query. 
            IF USER QUERY IS RUSSIAN, ANSWER TO USER IN RUSSIAN, IF USER QUERY IS ENGLISH, ANSWER TO USER IN ENGLISH.
            Dont tell user that you are helper, say that you are BI-GPT.
            
            User Query: {user_query}

            Here is some context for you:
            You are BI-GPT, you are a SQL expert with the connection to the database, you will be called ONLY in that cases when user is writing anything, but not requesting for data.
            SO BE A GOOD HELPER BOT FOR BI-GPT.
            YOU CAN SOME INTERESTING THINGS , ALSO YOU CAN HELP TO USER WRITE NL queries to BI-GPT.

            Database Schema:
                        {self.schema_info}

                        Policies:
                        {self.policies_info}
            """

            chatter_response = await self.llm.ainvoke(chatter_prompt)

            return {
                "success": True,
                "output": chatter_response.content,
                "intermediate_steps": []
            }
        else:
            pass
        
        try:
            if not self.schema_info:
                print("Fetching database metadata...")
                schema_result = await self.tools['sql_metainfo'].run()
                self.schema_info = schema_result.dict()
            
            if not self.policies_info:
                print("Fetching database policies...")
                policies_result = await self.tools['sql_policies'].run()
                self.policies_info = policies_result.dict()
            
            prompt = f"""You are a SQL expert. Based on the database schema and policies, generate a SQL query for this request: "{user_query}"

                        Database Schema:
                        {self.schema_info}

                        Policies:
                        {self.policies_info}

                        Generate a SQL query that:
                        1. Only uses allowed tables and columns
                        2. Avoids SELECT * - specify column names explicitly
                        3. Uses proper JOINs based on schema relationships
                        4. Follows the business rules from policies
                        5. Return the SQL query in a single line, without any explanations or comments, without any other text or formatting, no markdown formatting, DONT USE ```sql, without line breaks or any other characters

                        You MUST NEVER use COUNT(*). If you do, your query will be REJECTED.
                        Use COUNT(<allowed_column>) instead.

                        Bad → COUNT(*)
                        Good → COUNT(<allowed_column>)

                        Bad → SELECT c.city, COUNT(*) FROM clients c GROUP BY c.city
                        Good → SELECT c.city, COUNT(<allowed_column>) FROM clients c GROUP BY c.city

                        Return ONLY the SQL query, no explanations."""
            
            response = await self.llm.ainvoke(prompt)
            
            sql_query = response.content.strip().replace("```sql", "").replace("```", "")
            
            exec_result = await self.tools['sql_exec'].run({"sql": sql_query})
            exec_dict = exec_result.dict()
            
            analyser_prompt = f"""
            You are a SQL analyser. Analyse the SQL query and the execution result and return the analysis. Answer to user query based on data from execution result. Answer to user on language of user query.
            IF USER QUERY IS RUSSIAN, ANSWER TO USER IN RUSSIAN, IF USER QUERY IS ENGLISH, ANSWER TO USER IN ENGLISH.

            NO NEED TO WRITE EVERYTHING IN DETAIL, JUST ANSWER TO USER QUERY BASED ON DATA FROM EXECUTION RESULT. DONT MENTION POLICIES AND DATABASE INFO IN YOUR ANSWER.
            
            SQL Query: {sql_query}
            User Query: {user_query}

            Execution Result: {exec_dict}
            Some another data: {self.schema_info}
            Some another data: {self.policies_info}

            Return ONLY the analysis, explanations.

            dont return the sql query, only the analysis. IF ONLY query fails due to policy violation, say about it and explain PII policies, in another case just answer to user query based on data from execution result.
            """
            analyser_response = await self.llm.ainvoke(analyser_prompt)
            

            if exec_dict.get("success"):
                return {
                    "success": True,
                    "output": analyser_response.content,
                    "intermediate_steps": [
                        {"action": "sql_metainfo", "result": "metadata fetched"},
                        {"action": "sql_policies", "result": "policies fetched"},
                        {"action": "sql_generation", "result": sql_query},
                        {"action": "sql_exec", "result": exec_dict}
                    ]
                }
            else:
                return {
                    "success": False,
                    "output": analyser_response.content,
                    "intermediate_steps": [
                        {"action": "sql_metainfo", "result": "metadata fetched"},
                        {"action": "sql_policies", "result": "policies fetched"},
                        {"action": "sql_generation", "result": sql_query},
                        {"action": "sql_exec", "result": exec_dict}
                    ]
                }
                
        except Exception as e:
            return {
                "success": False,
                "output": f"Error processing request: {str(e)}",
                "intermediate_steps": []
            }


class LangChainSQLTool(BaseTool):
    
    tool_instance: Any = Field(exclude=True)
    
    def __init__(self, tool_instance, **kwargs):
        super().__init__(
            name=tool_instance.name,
            description=tool_instance.description,
            tool_instance=tool_instance,
            **kwargs
        )
    
    def _run(self, **kwargs) -> str:
        raise NotImplementedError("Use async run method")
    
    async def _arun(self, **kwargs) -> str:
        try:
            result = await self.tool_instance.run(kwargs)
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"


@dataclass
class BIGPTAgent:
    
    sql_client: SqlAdapterClient
    llm: ChatOpenAI
    agent_executor: AgentExecutor
    
    async def handle_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            result = await self.agent_executor.ainvoke({
                "input": message,
                "context": context or {}
            })
            
            return {
                "reply": result.get("output", "No response generated"),
                "tool_used": "langchain_agent",
                "tool_result": result,
                "success": result.get("success", False),
                "intermediate_steps": result.get("intermediate_steps", [])
            }
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Agent error: {error_details}")
            return {
                "reply": f"Error processing your request: {str(e)}",
                "tool_used": "langchain_agent",
                "tool_result": None,
                "error": str(e),
                "error_details": error_details
            }


async def create_bigpt_agent(sql_client: SqlAdapterClient, config=None) -> BIGPTAgent:
    
    if config is None:
        from ..config import get_config
        config = get_config()
    
    llm_kwargs = {
        "model": "llama4scout",
        "base_url": config.llm_base_url,
        "temperature": 0.1,
        "max_tokens": 2000
    }
    
    if config.llm_api_key:
        llm_kwargs["api_key"] = config.llm_api_key
    else:
        llm_kwargs["api_key"] = "dummy-key"
    
    llm = ChatOpenAI(**llm_kwargs)
    
    tools = {
        'sql_metainfo': SQLMetaInfoTool(sql_client),
        'sql_policies': SQLPoliciesTool(sql_client),
        'sql_exec': SQLExecTool(sql_client),
        'sql_explain': SQLExplainTool(sql_client)
    }
    
    try:
        print("Testing LLM connection...")
        test_response = await llm.ainvoke("Hello")
        print(f"LLM test successful: {test_response.content[:100]}...")
    except Exception as e:
        print(f"LLM connection test failed: {e}")
        raise e
    
    agent_executor = SimpleSQLAgent(llm, tools)
    
    return BIGPTAgent(
        sql_client=sql_client,
        llm=llm,
        agent_executor=agent_executor
    )


async def get_bigpt_agent(sql_client: SqlAdapterClient) -> BIGPTAgent:
    from ..config import get_config
    config = get_config()
    return await create_bigpt_agent(sql_client, config)
