import asyncio
from fastmcp import Client

client = Client("http://localhost:8001/mcp")

async def list_tools():
    async with client:
        result = await client.list_tools()
        print(result)

async def execute_query(query: str):
    async with client:
        result = await client.call_tool("execute_query", {"request": {"query": query}})
        print(result)



asyncio.run(list_tools())
asyncio.run(execute_query("SELECT avg(age) from clients;"))
