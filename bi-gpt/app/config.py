import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    sql_adapter_base_url: str = os.getenv("SQL_ADAPTER_BASE_URL", "http://localhost:8000")


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
