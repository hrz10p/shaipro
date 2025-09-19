import asyncio

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config
from app.models import ChatRequest, ChatResponse
from app.clients.http_client import SqlAdapterClient, get_sql_adapter_client, QueryResult, SQLQuery

from app.graph.factory import get_bigpt_graph
from app.config import get_config


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
    http_client: SqlAdapterClient = Depends(get_sql_adapter_client),  # 👈 тут
):
    config = get_config()
    graph = await get_bigpt_graph(http_client, config)

    initial_state = {
        "user_input": body.message,
        "context": body.context or {},
        "intermediate_steps": []
    }

    state = await graph.ainvoke(initial_state)

    return {
        "success": True,
        "output": state.get("final_text"),
        "route": state.get("route"),
        "sql": state.get("sql"),
        "intermediate_steps": state.get("intermediate_steps"),
        "exec_result": state.get("exec_result"),
    }

@app.post("/exec", response_model=QueryResult)
async def exec(
    body: SQLQuery,
    http_client: SqlAdapterClient = Depends(get_sql_adapter_client),
) -> QueryResult:
    return await http_client.exec(body.query)



@app.on_event("startup")
async def on_startup() -> None:
    await asyncio.sleep(0)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await asyncio.sleep(0)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
