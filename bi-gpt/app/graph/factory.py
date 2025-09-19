from app.graph.graph import build_bigpt_graph
from app.config import AppConfig

_graph = None

async def get_bigpt_graph(config: AppConfig):
    global _graph
    if _graph is None:
        _graph = build_bigpt_graph(config)
    return _graph
