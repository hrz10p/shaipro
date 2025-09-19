import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from schemas import SQLQuery, QueryResult, ExplainResult, MetaInfo, PolicyInfo
from explain_tools import flatten_plan_nodes, collect_relations, fetch_relation_sizes, estimate_bytes_scanned, generate_warnings
from policies import policy_manager
import sqlglot
from typing import Optional, Dict, Any, List

load_dotenv()


class DatabaseService:
    
    def __init__(self):
        self.policy_manager = policy_manager
    
    def get_db_connection(self):
        try:
            connection = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT', 5432),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            with connection.cursor() as cur:
                cur.execute("SET statement_timeout = 15000;")
                cur.execute("SET idle_in_transaction_session_timeout = 5000;")
                cur.execute("SET timezone TO 'Asia/Almaty';")
            return connection
        except Exception as e:
            raise Exception(f"Database connection failed: {str(e)}")
    
    def validate_sql_query(self, sql: str) -> tuple[bool, List[str]]:
        violations = []
        
        try:
            expr = sqlglot.parse_one(sql, dialect="postgres")
        except Exception as e:
            return False, [f"SQL parse error: {e}"]
        
        from sqlglot import exp
        if not isinstance(expr, exp.Select) and not expr.find(exp.Select, bfs=True):
            return False, ["Only SELECT statements are allowed"]
        
        stars = list(expr.find_all(exp.Star))
        for s in stars:
            func_parent = s.find_ancestor(exp.Func)
            print(f"func_parent: {func_parent}")
            if func_parent and func_parent.name == "COUNT" and func_parent.args[0].name == "*":
                continue
            violations.append("Wildcard '*' in projection is forbidden. List columns explicitly.")
        
        tables = [t.name for t in expr.find_all(exp.Table)]
        for t in tables:
            if not self.policy_manager.validate_table(t):
                violations.append(f"Table '{t}' is not allowed")
        
        cols = [c.name for c in expr.find_all(exp.Column)]
        for c in cols:
            if not self.policy_manager.validate_column(c):
                violations.append(f"Column '{c}' is forbidden by policy")
        
        funcs = [f.name for f in expr.find_all(exp.Func) if f.name]
        allowed_funcs = {f.lower() for f in self.policy_manager.allow_functions}
        for f in funcs:
            if allowed_funcs and f.lower() not in allowed_funcs:
                violations.append(f"Function '{f}' is not allowed")
        
        return len(violations) == 0, violations
    
    def execute_query(self, query_data: SQLQuery) -> QueryResult:
        conn = None
        try:
            sql = query_data.query.strip().rstrip(";")
            print(f"Received query: {sql}")
            
            is_valid, violations = self.validate_sql_query(sql)
            if not is_valid:
                return QueryResult(success=False, error="; ".join(violations))
            
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql)
            rows = cur.fetchall()
            data = [dict(row) for row in rows]
            return QueryResult(success=True, data=data, row_count=len(data))
            
        except Exception as e:
            if conn:
                conn.rollback()
            return QueryResult(success=False, error=str(e))
        finally:
            if conn:
                conn.close()
    
    def explain_query(self, query_data: SQLQuery) -> ExplainResult:
        conn = None
        try:
            sql = query_data.query.strip().rstrip(";")
            conn = self.get_db_connection()
            
            with conn.cursor() as cur:
                cur.execute(f"EXPLAIN (FORMAT JSON, COSTS TRUE, ANALYZE FALSE) {sql}")
                row = cur.fetchone()
            
            if not row:
                return ExplainResult(success=True, plan=[], mode="dry")
            
            plan_list = row[0]
            if isinstance(plan_list, list) and plan_list:
                plan = plan_list[0]
            else:
                plan = plan_list
            
            if not isinstance(plan, dict):
                return ExplainResult(success=False, error="Unexpected EXPLAIN format", plan=[], mode="dry")
            
            top = plan.get("Plan", {})
            nodes = flatten_plan_nodes(plan)
            rels = collect_relations(nodes)
            rel_sizes = fetch_relation_sizes(conn, rels)
            
            est_cost = float(top.get("Total Cost") or 0.0)
            est_rows = int(top.get("Plan Rows") or 0)
            est_bytes = estimate_bytes_scanned(nodes, rel_sizes)
            
            warnings, violations = generate_warnings(sql, nodes, est_cost, est_rows, est_bytes, rel_sizes)
            
            return ExplainResult(
                success=True,
                mode="dry",
                plan=[plan],
                nodes=nodes,
                rel_sizes=rel_sizes,
                est_cost=est_cost,
                est_rows=est_rows,
                est_bytes_scanned=est_bytes,
                warnings=warnings,
                violations=violations
            )
        except Exception as e:
            return ExplainResult(success=False, error=str(e), plan=[], mode="dry")
        finally:
            if conn:
                conn.close()
    
    def get_meta_info(self) -> MetaInfo:
        connection = None
        try:
            print("getMetainfo called")
            connection = self.get_db_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    current_database() as database_name,
                    version() as version,
                    current_user as current_user
            """)
            db_info = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    tableowner,
                    hasindexes,
                    hasrules,
                    hastriggers,
                    rowsecurity
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY schemaname, tablename
            """)
            tables = cursor.fetchall()
            
            tables_with_columns = []
            for table in tables:
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (table['schemaname'], table['tablename']))
                
                columns = cursor.fetchall()
                table_dict = dict(table)
                table_dict['columns'] = [dict(col) for col in columns]
                tables_with_columns.append(table_dict)
            
            enumerables = [e.split(".") for e in self.policy_manager.enumerables]
            enumerables_with_values = []
            for e in enumerables:
                table, column = e
                cursor.execute(f"SELECT DISTINCT {column} FROM {table}")
                values = cursor.fetchall()
                enumerables_with_values.append({
                    "table": table,
                    "column": column,
                    "values": values
                })
            
            return MetaInfo(
                success=True,
                database_info=dict(db_info),
                tables=tables_with_columns,
                enumerables=enumerables_with_values
            )
            
        except Exception as e:
            return MetaInfo(
                success=False,
                error=str(e)
            )
        finally:
            if connection:
                connection.close()
    
    def get_policies(self) -> PolicyInfo:
        try:
            return PolicyInfo(
                success=True,
                policies={
                    "allow_tables": self.policy_manager.allow_tables,
                    "deny_columns": self.policy_manager.deny_columns,
                    "allow_functions": self.policy_manager.allow_functions,
                    "join_graph": self.policy_manager.join_graph,
                    "limits": self.policy_manager.limits,
                    "glossary": self.policy_manager.glossary,
                }
            )
        except Exception as e:
            return PolicyInfo(success=False, policies={}, error=str(e))


db_service = DatabaseService()
