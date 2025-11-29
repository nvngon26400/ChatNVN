from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, Docx2txtLoader, PyPDFLoader

from .config import Settings


def load_documents(settings: Settings) -> List[Document]:
    """Load PDF and DOCX documents from the configured directory."""

    docs_path = settings.docs_path
    if not docs_path.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_path}")

    loader = DirectoryLoader(
        str(docs_path),
        glob="**/*",
        show_progress=True,
        use_multithreading=True,
        loader_cls=_select_loader,
    )
    documents = loader.load()

    if not documents:
        raise ValueError(f"No PDF/DOCX files found under {docs_path}.")

    return documents


def _select_loader(file_path: str) -> PyPDFLoader | Docx2txtLoader:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(file_path)
    if path.suffix.lower() in {".doc", ".docx"}:
        return Docx2txtLoader(file_path)
    if path.suffix.lower() == ".txt":
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path, encoding="utf-8")
    raise ValueError(f"Unsupported file type for loader: {file_path}")


def split_documents(settings: Settings, documents: Iterable[Document]) -> List[Document]:
    """Split documents into overlapping chunks for retrieval."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
    )
    return splitter.split_documents(list(documents))


