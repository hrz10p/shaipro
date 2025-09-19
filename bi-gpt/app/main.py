import asyncio
from typing import Optional

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config
from app.schemas import ChatRequest, ChatResponse
from app.clients.http_client import SqlAdapterClient, get_sql_adapter_client, QueryResult, SQLQuery
from app.memory_service import memory_service
from app.graph.factory import get_bigpt_graph


app = FastAPI(title="bi-gpt", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(request: Request) -> dict:
    print("Client address: ", request.client.host, request.client.port)
    return {"status": "ok"}


@app.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    response: Response,
):
    session_id = request.cookies.get("sessionId")
    session_id = memory_service.get_or_create_session(session_id)
    
    response.set_cookie(
        key="sessionId", 
        value=session_id, 
        max_age=86400 * 30,  # 30 days
        httponly=True,
        samesite="lax"
    )
    
    memory_context = memory_service.get_session_context(session_id)
    
    config = get_config()
    graph = await get_bigpt_graph(config)

    user_input_with_context = body.message
    if memory_context:
        user_input_with_context = f"Previous conversation context:\n{memory_context}\n\nCurrent question: {body.message}"

    initial_state = {
        "user_input": user_input_with_context,
        "context": body.context or {},
        "intermediate_steps": []
    }

    state = await graph.ainvoke(initial_state)
    
    memory_service.add_message(session_id, body.message, "user")
    memory_service.add_message(session_id, state.get("final_text", ""), "assistant")

    return {
        "success": True,
        "output": state.get("final_text"),
        "route": state.get("route"),
        "sql": state.get("sql"),
        "intermediate_steps": state.get("intermediate_steps"),
        "exec_result": state.get("exec_result"),
        "visualization": state.get("visualization"),
    }

@app.post("/exec", response_model=QueryResult)
async def exec(
    body: SQLQuery,
    http_client: SqlAdapterClient = Depends(get_sql_adapter_client),
) -> QueryResult:
    return await http_client.exec(body.query)


@app.post("/clear-memory")
async def clear_memory(
    request: Request,
    response: Response,
):
    session_id = request.cookies.get("sessionId")
    if session_id:
        memory_service.clear_session(session_id)
        return {"success": True, "message": "Memory cleared"}
    return {"success": False, "message": "No session found"}



@app.on_event("startup")
async def on_startup() -> None:
    await asyncio.sleep(0)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await asyncio.sleep(0)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8060)
