from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from .config import Settings


class VectorStoreBuilder:
    """Wrap FAISS construction for easier testing and swapping."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    def build(self, documents: Iterable[Document], persist_path: Optional[Path] = None) -> FAISS:
        vector_store = FAISS.from_documents(documents=list(documents), embedding=self._embeddings)

        if persist_path:
            persist_path.parent.mkdir(parents=True, exist_ok=True)
            vector_store.save_local(str(persist_path))

        return vector_store

    def load_from_disk(self, persist_path: Path) -> FAISS:
        return FAISS.load_local(
            str(persist_path),
            embeddings=self._embeddings,
            allow_dangerous_deserialization=True,
        )


def get_retriever(vector_store: FAISS, k: int = 4) -> BaseRetriever:
    return vector_store.as_retriever(search_kwargs={"k": k})


