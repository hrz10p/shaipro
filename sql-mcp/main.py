from fastapi import FastAPI, HTTPException
from schemas import SQLQuery, QueryResult, ExplainResult, MetaInfo, PolicyInfo
from service import db_service

app = FastAPI(title="SQL MCP", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "SQL MCP is running"}

@app.post("/exec", response_model=QueryResult)
async def execute_query(query_data: SQLQuery):
    return db_service.execute_query(query_data)


@app.post("/explain", response_model=ExplainResult)
async def explain_query(query_data: SQLQuery):
    return db_service.explain_query(query_data)


@app.get("/getMetainfo", response_model=MetaInfo)
async def get_meta_info():
    return db_service.get_meta_info()

@app.get("/getPolicies", response_model=PolicyInfo)
async def get_policies():
    return db_service.get_policies()

if __name__ == "__main__":
    import sys
    import uvicorn
    from mcp_server import run_mcp_server
    
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        print("Starting SQL MCP server...")
        run_mcp_server(host="0.0.0.0", port=8001)
    else:
        print("Starting SQL MCP server as HTTP server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)