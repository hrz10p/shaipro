import json
from fastmcp import FastMCP
from service import db_service
from schemas import QueryResult, SQLQuery, ExplainResult, MetaInfo, PolicyInfo

mcp = FastMCP("SQL MCP")

@mcp.tool()
def execute_query(request: SQLQuery) -> QueryResult:
    """
    Execute a SQL SELECT query against the database.
    
    Args:
        request: Contains the SQL query to execute
        
    Returns:
        QueryResponse with query results or error information
    """
    try:
        query_data = SQLQuery(query=request.query)
        result = db_service.execute_query(query_data)
        
        return QueryResult(
            success=result.success,
            data=result.data,
            row_count=result.row_count,
            error=result.error
        )
    except Exception as e:
        return QueryResult(
            success=False,
            error=f"Execution error: {str(e)}"
        )


@mcp.tool()
def explain_query(request: SQLQuery) -> ExplainResult:
    """
    Get execution plan and analysis for a SQL query.
    
    Args:
        request: Contains the SQL query to explain
        
    Returns:
        ExplainResponse with execution plan details or error information
    """
    try:
        query_data = SQLQuery(query=request.query)
        result = db_service.explain_query(query_data)
        
        return ExplainResult(
            success=result.success,
            mode=result.mode,
            plan=result.plan,
            nodes=result.nodes,
            rel_sizes=result.rel_sizes,
            est_cost=result.est_cost,
            est_rows=result.est_rows,
            est_bytes_scanned=result.est_bytes_scanned,
            warnings=result.warnings,
            violations=result.violations,
            error=result.error
        )
    except Exception as e:
        return ExplainResult(
            success=False,
            error=f"Explain error: {str(e)}"
        )


@mcp.tool()
def get_metainfo() -> MetaInfo:
    """
    Get database metadata including tables, columns, and enumerables.
    
    Returns:
        MetaInfoResponse with database schema information
    """
    try:
        result = db_service.get_meta_info()
        
        return MetaInfo(
            success=result.success,
            database_info=result.database_info,
            tables=result.tables,
            enumerables=result.enumerables,
            error=result.error
        )
    except Exception as e:
        return MetaInfo(
            success=False,
            error=f"Meta info error: {str(e)}"
        )


@mcp.tool()
def get_policies() -> PolicyInfo:
    """
    Get current database access policies and configuration.
    
    Returns:
        PoliciesResponse with policy information
    """
    try:
        result = db_service.get_policies()
        
        return PolicyInfo(
            success=result.success,
            policies=result.policies,
            error=result.error
        )
    except Exception as e:
        return PolicyInfo(
            success=False,
            error=f"Policies error: {str(e)}"
        )

@mcp.resource("db://policies")
def get_policies_resource() -> str:
    """Get policies as a resource"""
    result = db_service.get_policies()
    if result.success:
        return json.dumps({
            "success": True,
            "policies": result.policies
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": result.error
        }, indent=2)


@mcp.resource("db://meta")
def get_meta_resource() -> str:
    """Get database metadata as a resource"""
    result = db_service.get_meta_info()
    if result.success:
        return json.dumps({
            "success": True,
            "database_info": result.database_info,
            "tables": result.tables,
            "enumerables": result.enumerables
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": result.error
        }, indent=2)


def run_mcp_server(host: str = "0.0.0.0", port: int = 8001):
    """
    Run the MCP server using FastMCP.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
    """
    print(f"Starting SQL Proxy Adapter MCP server on {host}:{port}")
    mcp.run(transport="http",host=host, port=port)


if __name__ == "__main__":
    
    
    host = "0.0.0.0"
    port = 8001
    
    
    run_mcp_server(host=host, port=port)