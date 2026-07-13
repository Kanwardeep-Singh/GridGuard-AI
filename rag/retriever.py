"""Thin retrieval interface used by the ICS Knowledge Agent."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from rag.vectorstore import VectorStore


class Retriever:
    def __init__(self, store: VectorStore | None = None):
        self._store = store

    def _ensure_store(self) -> VectorStore:
        if self._store is not None:
            return self._store
        index_path = None
        try:
            self._store = VectorStore.load()
        except Exception:
            # No persisted index yet - build one on the fly from the knowledge base.
            self._store = VectorStore().build()
        return self._store

    def retrieve(self, query: str, top_k: int = 4) -> list[str]:
        store = self._ensure_store()
        results = store.search(query, top_k=top_k)
        return [f"[{chunk.source}] {chunk.text.strip()[:300]}" for chunk, _score in results]
