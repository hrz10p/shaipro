import math, random, datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

def _serialize_value(v):
    """Convert pandas/np types to plain Python types suitable for JSON/display."""
    if pd.isna(v):
        return None
    if isinstance(v, (np.floating, float)):
        return float(v)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (pd.Timestamp, datetime.datetime)):
        return v.isoformat()
    # numpy bool etc.
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    return v

def _clean_numeric_data(data: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    """Clean numeric data that might contain concatenated numbers separated by dots."""
    cleaned_data = []
    for row in data:
        cleaned_row = {}
        for key, value in row.items():
            if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                if value.count('.') > 1 and len(value) > 20:
                    try:
                        parts = value.split('.')
                        if parts[0]:
                            cleaned_value = float(parts[0])
                        else:
                            cleaned_value = float(''.join(parts))
                    except (ValueError, IndexError):
                        try:
                            cleaned_value = float(value)
                        except ValueError:
                            cleaned_value = 0.0
                else:
                    try:
                        cleaned_value = float(value)
                    except ValueError:
                        cleaned_value = 0.0
                cleaned_row[key] = cleaned_value
            else:
                cleaned_row[key] = value
        cleaned_data.append(cleaned_row)
    return cleaned_data

def _records_serializable(df: pd.DataFrame) -> List[Dict[str,Any]]:
    recs = df.to_dict(orient='records')
    return [{k: _serialize_value(v) for k,v in r.items()} for r in recs]

def make_histogram_payload(data: List[Dict[str,Any]], x_field: str="x", bins:int=10, title:Optional[str]=None):
    df = pd.DataFrame(data)
    if x_field not in df.columns:
        raise ValueError(f"x_field '{x_field}' not found")
    x = pd.to_numeric(df[x_field], errors="coerce").dropna().astype(float)
    counts, edges = np.histogram(x.values, bins=bins)
    total = int(counts.sum())
    out = []
    for i in range(len(counts)):
        out.append({
            "bin_start": float(edges[i]),
            "bin_end": float(edges[i+1]),
            "count": int(counts[i]),
            "pct": float(counts[i]) / total if total>0 else 0.0
        })
    meta = {"title": title or f"Histogram of {x_field}", "x_label": x_field, "y_label": "count",
            "tooltip_fields": ["bin_start","bin_end","count","pct"]}
    for row in out:
        for k in list(row.keys()):
            row[k] = _serialize_value(row[k])
    return {"chart_type":"histogram","meta":meta,"data":out}

def make_pie_payload(data: List[Dict[str,Any]], group_by: str, y_field: Optional[str]=None, aggregate: str="sum", title:Optional[str]=None):
    df = pd.DataFrame(data)
    if group_by not in df.columns:
        raise ValueError(f"group_by '{group_by}' not found")
    if y_field and y_field in df.columns and aggregate != "count":
        if aggregate == "mean":
            grouped = df.groupby(group_by)[y_field].mean()
        else:
            grouped = df.groupby(group_by)[y_field].sum()
    else:
        grouped = df.groupby(group_by).size().rename("value")
    grouped = grouped.sort_values(ascending=False)
    total = float(grouped.sum()) if grouped.sum() is not None else 0.0
    out = []
    for n,v in grouped.items():
        out.append({"name": str(n), "value": float(v), "pct": (float(v)/total if total>0 else 0.0)})
    for row in out:
        for k in list(row.keys()):
            row[k] = _serialize_value(row[k])
    meta = {"title": title or f"Pie: {group_by}", "tooltip_fields":["name","value","pct"]}
    return {"chart_type":"pie","meta":meta,"data":out}

def make_scatter_payload(data: List[Dict[str,Any]], x_field: str="x", y_field: str="y", extra_fields: Optional[List[str]]=None, title:Optional[str]=None):
    df = pd.DataFrame(data)
    if x_field not in df.columns or y_field not in df.columns:
        raise ValueError("scatter requires x_field and y_field present")
    x = pd.to_numeric(df[x_field], errors="coerce")
    y = pd.to_numeric(df[y_field], errors="coerce")
    out_df = pd.DataFrame({"x": x, "y": y})
    if extra_fields:
        for f in extra_fields:
            if f in df.columns:
                out_df[f] = df[f]
    out_df = out_df.dropna(subset=["x","y"]).reset_index(drop=True)
    data_out = _records_serializable(out_df)
    meta = {"title": title or f"Scatter {y_field} vs {x_field}", "x_label": x_field, "y_label": y_field,
            "tooltip_fields": ["x","y"] + (extra_fields or [])}
    return {"chart_type":"scatter","meta":meta,"data":data_out}

def make_line_payload(data: List[Dict[str,Any]], x_field: str="x", y_field: str="y", aggregate: str="sum", time_freq: Optional[str]=None, title:Optional[str]=None):
    df = pd.DataFrame(data)
    if x_field not in df.columns or y_field not in df.columns:
        raise ValueError("line requires x_field and y_field present")
    if time_freq:
        tmp = df.copy()
        tmp[x_field] = pd.to_datetime(tmp[x_field], errors="coerce")
        tmp[y_field] = pd.to_numeric(tmp[y_field], errors="coerce").fillna(0.0)
        tmp = tmp.dropna(subset=[x_field])
        tmp = tmp.set_index(x_field)
        agg = getattr(tmp[y_field].resample(time_freq), aggregate)()
        out_df = agg.reset_index().rename(columns={x_field:"x", y_field:"y"})
    else:
        tmp = df[[x_field,y_field]].copy()
        tmp[y_field] = pd.to_numeric(tmp[y_field], errors="coerce")
        if aggregate=="mean":
            grouped = tmp.groupby(x_field)[y_field].mean()
        else:
            grouped = tmp.groupby(x_field)[y_field].sum()
        out_df = grouped.reset_index().rename(columns={x_field:"x", y_field:"y"})
    out_df = out_df.dropna(subset=["x","y"])
    try:
        out_df = out_df.sort_values(by="x")
    except Exception:
        pass
    data_out = _records_serializable(out_df)
    meta = {"title": title or f"Line {y_field} over {x_field}", "x_label": x_field, "y_label": y_field,
            "tooltip_fields":["x","y"]}
    return {"chart_type":"line","meta":meta,"data":data_out}

def _get_available_columns(data: List[Dict[str,Any]]) -> List[str]:
    """Get available column names from data."""
    if not data:
        return []
    return list(data[0].keys()) if data else []

def _find_numeric_column(data: List[Dict[str,Any]], preferred_names: List[str] = None) -> str:
    """Find the first numeric column in data."""
    if not data:
        return "value"
    
    df = pd.DataFrame(data)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if preferred_names:
        for name in preferred_names:
            if name in numeric_cols:
                return name
    
    return numeric_cols[0] if numeric_cols else df.columns[0]

def _find_categorical_column(data: List[Dict[str,Any]], preferred_names: List[str] = None) -> str:
    """Find the first categorical column in data."""
    if not data:
        return "category"
    
    df = pd.DataFrame(data)
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    if preferred_names:
        for name in preferred_names:
            if name in categorical_cols:
                return name
    
    return categorical_cols[0] if categorical_cols else df.columns[0]

def send_to_tool(chart_type: str, data: List[Dict[str,Any]], options: Dict[str,Any]=None):
    """Create visualization with smart field detection."""
    if not data:
        return {
            "chart_type": "error",
            "meta": {"title": "No Data", "error": "No data available for visualization"},
            "data": []
        }
    
    try:
        data = _clean_numeric_data(data)
    except Exception as e:
        return {
            "chart_type": "error",
            "meta": {"title": "Data Processing Error", "error": f"Failed to clean data: {str(e)}"},
            "data": []
        }
    
    opts = options or {}
    available_cols = _get_available_columns(data)
    
    if chart_type == "histogram":
        x_field = opts.get("x_field") or _find_numeric_column(data, ["value", "count", "amount", "total"])
        return make_histogram_payload(data, x_field=x_field, bins=opts.get("bins",10), title=opts.get("title"))
    
    elif chart_type == "pie":
        group_by = opts.get("group_by") or _find_categorical_column(data, ["category", "type", "name", "label"])
        y_field = opts.get("y_field") or _find_numeric_column(data, ["amount", "count", "value", "total"])
        return make_pie_payload(data, group_by=group_by, y_field=y_field, aggregate=opts.get("aggregate","sum"), title=opts.get("title"))
    
    elif chart_type == "scatter":
        x_field = opts.get("x_field") or _find_numeric_column(data, ["x", "value", "amount"])
        y_field = opts.get("y_field") or _find_numeric_column(data, ["y", "count", "total"])
        return make_scatter_payload(data, x_field=x_field, y_field=y_field, extra_fields=opts.get("extra_fields"), title=opts.get("title"))
    
    elif chart_type == "line":
        x_field = opts.get("x_field") or _find_categorical_column(data, ["date", "time", "dt", "x"])
        y_field = opts.get("y_field") or _find_numeric_column(data, ["value", "amount", "count", "y"])
        return make_line_payload(data, x_field=x_field, y_field=y_field, aggregate=opts.get("aggregate","mean"), time_freq=opts.get("time_freq","D"), title=opts.get("title"))
    
    else:
        raise ValueError("unsupported chart_type: " + str(chart_type))