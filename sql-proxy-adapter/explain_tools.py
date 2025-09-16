from typing import List, Dict, Any, Tuple
import re
import os

MAX_COST = float(os.getenv("MAX_COST", "5e7"))
MAX_BYTES_SCANNED = int(os.getenv("MAX_BYTES_SCANNED", str(2 * 1024**3)))  # 2 GB
MAX_EST_ROWS = int(os.getenv("MAX_EST_ROWS", "20000000"))  # 20M

DATE_COL_RE = re.compile(r"\b(date|_at|_time)\b", re.IGNORECASE)

def flatten_plan_nodes(plan_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    def walk(node: Dict[str, Any]):
        if not node: return
        cur = {
            "type": node.get("Node Type"),
            "relation": node.get("Relation Name"),
            "alias": node.get("Alias"),
            "plan_rows": node.get("Plan Rows"),
            "plan_width": node.get("Plan Width"),
            "total_cost": node.get("Total Cost"),
            "startup_cost": node.get("Startup Cost"),
        }
        out.append(cur)
        for child_key in ("Plans", "Inner Unique", "Outer Unique"):
            ch = node.get(child_key)
            if isinstance(ch, list):
                for c in ch:
                    walk(c)
            elif isinstance(ch, dict):
                walk(ch)
        for c in node.get("Plans", []) or []:
            walk(c)
    walk(plan_json.get("Plan", {}))
    return out

def collect_relations(nodes: List[Dict[str, Any]]) -> List[str]:
    rels = []
    for n in nodes:
        rel = n.get("relation")
        if rel and rel not in rels:
            rels.append(rel)
    return rels

def fetch_relation_sizes(conn, rels: List[str]) -> Dict[str, int]:
    if not rels: return {}
    q = """
    SELECT relname, pg_total_relation_size(oid) AS size
    FROM pg_class
    WHERE relkind IN ('r','m','f','p','v') AND relname = ANY(%s)
    """
    with conn.cursor() as cur:
        cur.execute(q, (rels,))
        rows = cur.fetchall()
    return {r[0]: int(r[1]) for r in rows}

def estimate_bytes_scanned(nodes: List[Dict[str, Any]], rel_sizes: Dict[str, int]) -> int:
    total = 0
    for n in nodes:
        if n.get("type") == "Seq Scan":
            rel = n.get("relation")
            if rel and rel in rel_sizes:
                total += rel_sizes[rel]
        elif n.get("type") in ("Index Scan","Index Only Scan"):
            rows = n.get("plan_rows") or 0
            width = n.get("plan_width") or 64
            total += int(rows * width)
        elif n.get("type") in ("Hash","Sort","Aggregate","GroupAggregate","HashAggregate"):
            rows = n.get("plan_rows") or 0
            width = n.get("plan_width") or 64
            total += int(rows * width)
    return total

def has_limit(sql: str) -> bool:
    return " limit " in sql.lower()

def has_time_filter(sql: str) -> bool:
    s = sql.lower()
    return (" where " in s) and bool(DATE_COL_RE.search(s))

def generate_warnings(sql: str, nodes: List[Dict[str, Any]], est_cost: float, est_rows: int,
                      est_bytes: int, rel_sizes: Dict[str, int]) -> Tuple[List[str], List[str]]:
    warnings, violations = [], []
    if not has_limit(sql):
        warnings.append("missing LIMIT")
    if not has_time_filter(sql):
        warnings.append("missing time/date filter (heuristic)")

    if any(n.get("type") == "Seq Scan" for n in nodes):
        # warnings.append("sequential scan detected")
        pass
    if est_rows and est_rows > MAX_EST_ROWS:
        warnings.append(f"too many rows estimated (> {MAX_EST_ROWS:,})")
    if est_cost and est_cost > MAX_COST:
        violations.append(f"estimated cost exceeds budget ({est_cost:.0f} > {MAX_COST:.0f})")
    if est_bytes and est_bytes > MAX_BYTES_SCANNED:
        violations.append(f"estimated bytes scanned exceeds budget ({est_bytes:,} > {MAX_BYTES_SCANNED:,})")

    big_seq = []
    for n in nodes:
        if n.get("type") == "Seq Scan":
            rel = n.get("relation")
            sz = rel_sizes.get(rel or "", 0)
            if sz >= MAX_BYTES_SCANNED // 2:
                big_seq.append(f"{rel} ~ {sz:,} bytes")
    if big_seq:
        warnings.append("seq scan on large relation(s): " + ", ".join(big_seq))

    return warnings, violations