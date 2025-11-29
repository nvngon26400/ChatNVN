from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    """Runtime configuration derived from environment variables."""

    openai_api_key: str
    chat_model: str
    embedding_model: str
    docs_path: Path
    chat_temperature: float = 1.0
    max_tokens: int = 512
    llm_timeout: int = 30
    llm_max_retries: int = 1
    chunk_size: int = 800
    chunk_overlap: int = 150
    retriever_k: int = 3
    persist_index: bool = True
    persist_index_path: Path = Path("data/faiss")
    reindex_on_start: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_endpoint: Optional[str] = "https://api.smith.langchain.com"
    langsmith_project: Optional[str] = "mock-support-chatbot"
    tracing_enabled: bool = False

    @property
    def docs_exist(self) -> bool:
        return self.docs_path.exists() and any(self.docs_path.glob("*"))


def get_settings() -> Settings:
    """Load settings from environment variables and enforce required keys."""

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set. Update .env before running the chatbot.")

    chat_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Sanity check: nếu model không được tiktoken hỗ trợ, tự động fallback
    try:
        import tiktoken  # type: ignore
        try:
            _ = tiktoken.encoding_for_model(chat_model)
        except Exception:
            chat_model = "gpt-4o-mini"
    except Exception:
        # Nếu không có tiktoken, vẫn fallback khi thấy tên model không chuẩn
        if "gpt-5" in chat_model:
            chat_model = "gpt-4o-mini"
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    docs_path = Path(os.getenv("DOCS_PATH", "data/docs")).resolve()
    max_tokens = int(os.getenv("MAX_TOKENS", 512))
    llm_timeout = int(os.getenv("LLM_TIMEOUT", 30))
    llm_max_retries = int(os.getenv("LLM_MAX_RETRIES", 1))
    retriever_k = int(os.getenv("RETRIEVER_K", 3))
    persist_index = os.getenv("PERSIST_INDEX", "true").lower() == "true"
    persist_index_path = Path(os.getenv("PERSIST_INDEX_PATH", "data/faiss")).resolve()
    reindex_on_start = os.getenv("REINDEX_ON_START", "false").lower() == "true"

    langsmith_api_key = os.getenv("LANGCHAIN_API_KEY")
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true" and bool(
        langsmith_api_key
    )

    settings = Settings(
        openai_api_key=openai_api_key,
        chat_model=chat_model,
        chat_temperature=float(os.getenv("CHAT_TEMPERATURE", 1.0)),
        max_tokens=max_tokens,
        llm_timeout=llm_timeout,
        llm_max_retries=llm_max_retries,
        embedding_model=embedding_model,
        docs_path=docs_path,
        chunk_size=int(os.getenv("CHUNK_SIZE", 800)),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 150)),
        retriever_k=retriever_k,
        persist_index=persist_index,
        persist_index_path=persist_index_path,
        reindex_on_start=reindex_on_start,
        langsmith_api_key=langsmith_api_key,
        langsmith_endpoint=os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
        langsmith_project=os.getenv("LANGCHAIN_PROJECT", "mock-support-chatbot"),
        tracing_enabled=tracing_enabled,
    )

    if settings.tracing_enabled:
        _configure_langsmith(settings)

    return settings


def _configure_langsmith(settings: Settings) -> None:
    """Set LangSmith environment variables if tracing is enabled."""

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint or ""
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key or ""
    if settings.langsmith_project:
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project


